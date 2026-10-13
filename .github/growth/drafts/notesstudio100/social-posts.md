# 100 Notes Studio：四語貼文（notesstudio100-01）

| 項目 | 內容 |
|---|---|
| 用途 | 搭配三支示範影片的文字貼文；台灣國考、日本買い切り、韓國평생소장、英文隱私手寫族各一則 |
| 平台／對象 | zh-Hant／ja／ko：Threads（ko 也可用 Instagram 說明）；en：Threads 或 Bluesky |
| 發文者 | 店主 Guan Feng Lai，用**本人帳號**，正文已寫明開發者身分 |
| 發文規則 | 每帳號每天最多 3 則、同一則 21 天內不重發；正文不放連結，連結放第一則留言或簡介；hashtag 最多 2 個；不比較他牌、不寫排名用語；免費額度一律寫「1 本最多 5 頁、2 款風格」 |
| 事實依據 | App Store 商店文案（2026-10-13 lookup，US／TW／JP／KR）；介面 50 種語言、App 內切換（店主確認） |

> `app-posts.json` 已有第一輪（ct=`notesstudio1_*`）。本檔是第二輪，ct 依 notesstudio100-01 指定的 `n100_*` 命名。

---

### 台灣國考生：講義、筆記、複習卡分散在三個地方
- lang: zh-Hant
- ct: n100_tw_exam
- 平台: Threads
- 連結（放第一則留言）: https://apps.apple.com/app/id6798813048?pt=118326163&ct=n100_tw_exam&mt=8

```text
準備國考，講義多半是 PDF，筆記在另一個地方，複習卡又開第三個 App。

我是 100 Notes Studio 的開發者，想把這三件事放回同一本：PDF 講義直接標註；上課錄音存在開始錄的那一頁；從筆記頁建立抽認卡和填空卡，用 FSRS 間隔重複排複習。手寫字在裝置上辨識，搜得到。

不需帳號、沒有廣告、不用外部 AI，核心功能離線可用。免費版是 1 本最多 5 頁的筆記本和 2 款風格，100 款風格都能先預覽；要更多頁數和筆記本，一次購買，不是訂閱。介面 50 種語言，App 內切換。
```

### 日本：ノートは何年も書き足すもの（買い切り）
- lang: ja
- ct: n100_jp_kaikiri
- 平台: Threads
- 連結（放第一則留言）: https://apps.apple.com/app/id6798813048?pt=118326163&ct=n100_jp_kaikiri&mt=8

```text
ノートは何年も書き足していくもの。だから 100 Notes Studio は、追加機能を一度買えば使い続けられる形にしました（開発者です）。

万年筆・筆ペン・水彩など29種類のペンとブラシ。表紙から用紙の構成、仕切り、シールまで違う100種類のスタイルは、購入前に全部プレビューできます。PDFへの書き込み、ページに残る録音、FSRSの暗記カードも。

アカウント不要・広告なし・外部AIなし。無料版はノート1冊（5ページまで）とスタイル2種です。表示言語は50種類、アプリ内で切替可。
```

### 韓國：找能평생소장的手寫筆記 App
- lang: ko
- ct: n100_kr_lifetime
- 平台: Threads／Instagram
- 連結（放第一則留言或簡介）: https://apps.apple.com/app/id6798813048?pt=118326163&ct=n100_kr_lifetime&mt=8

```text
구독 없이 오래 쓸 필기 앱을 찾고 있다면 100 Notes Studio를 한번 봐 주세요. 대만에서 혼자 앱을 만드는 개발자입니다.

추가 기능은 한 번만 구매하면 됩니다. 만년필·붓펜·수채 브러시 등 펜과 브러시 29종, 표지부터 속지 구조·간지·스티커까지 다른 스타일 100종(구매 전 전부 미리보기), PDF 주석, 페이지에 붙는 녹음, FSRS 암기카드.

계정·광고 없음, 손글씨 인식과 검색은 기기에서 처리. 무료는 노트 1권(최대 5페이지)과 스타일 2종입니다. 인터페이스 50개 언어, 앱 안에서 전환.
```

### 英文：不要帳號、不要廣告、不送外部 AI 的手寫 App
- lang: en
- ct: n100_us_private
- 平台: Threads／Bluesky
- 連結（放第一則留言）: https://apps.apple.com/app/id6798813048?pt=118326163&ct=n100_us_private&mt=8

```text
A handwriting app with no account, no ads and no external AI reading your pages. That was the brief I gave myself for 100 Notes Studio (I'm the developer).

29 pens and brushes. 100 notebook styles that differ in cover, paper and dividers, all previewable. PDF markup, audio attached to the page, on-device handwriting search, FSRS flashcards.

Free: 1 notebook of up to 5 pages and 2 styles. The upgrade is a one-time purchase. Interface in 50 languages, switch in-app.
```

## 給本機 Claude：併入 app-posts.json 的條目

這次雲端工作只能寫 `drafts/`，所以沒有動 `app-posts.json`。本機 Claude 審過後，可把下列物件直接加進 `posts` 陣列（`ct` 都是新的，不與第一輪重複）。

| ct | lang | 字元數（Threads 上限 500） |
|---|---|---|
| n100_tw_exam | zh-Hant | 250 |
| n100_jp_kaikiri | ja | 245 |
| n100_kr_lifetime | ko | 290 |
| n100_us_private | en | 470 |

```json
[
 {
  "app": "notesstudio100",
  "app_id": "6798813048",
  "lang": "zh-Hant",
  "scenario": "台灣國考生：講義、筆記、複習卡分散在三個地方",
  "ct": "n100_tw_exam",
  "text": "準備國考，講義多半是 PDF，筆記在另一個地方，複習卡又開第三個 App。\n\n我是 100 Notes Studio 的開發者，想把這三件事放回同一本：PDF 講義直接標註；上課錄音存在開始錄的那一頁；從筆記頁建立抽認卡和填空卡，用 FSRS 間隔重複排複習。手寫字在裝置上辨識，搜得到。\n\n不需帳號、沒有廣告、不用外部 AI，核心功能離線可用。免費版是 1 本最多 5 頁的筆記本和 2 款風格，100 款風格都能先預覽；要更多頁數和筆記本，一次購買，不是訂閱。介面 50 種語言，App 內切換。"
 },
 {
  "app": "notesstudio100",
  "app_id": "6798813048",
  "lang": "ja",
  "scenario": "日本：ノートは何年も書き足すもの（買い切り）",
  "ct": "n100_jp_kaikiri",
  "text": "ノートは何年も書き足していくもの。だから 100 Notes Studio は、追加機能を一度買えば使い続けられる形にしました（開発者です）。\n\n万年筆・筆ペン・水彩など29種類のペンとブラシ。表紙から用紙の構成、仕切り、シールまで違う100種類のスタイルは、購入前に全部プレビューできます。PDFへの書き込み、ページに残る録音、FSRSの暗記カードも。\n\nアカウント不要・広告なし・外部AIなし。無料版はノート1冊（5ページまで）とスタイル2種です。表示言語は50種類、アプリ内で切替可。"
 },
 {
  "app": "notesstudio100",
  "app_id": "6798813048",
  "lang": "ko",
  "scenario": "韓國：找能평생소장的手寫筆記 App",
  "ct": "n100_kr_lifetime",
  "text": "구독 없이 오래 쓸 필기 앱을 찾고 있다면 100 Notes Studio를 한번 봐 주세요. 대만에서 혼자 앱을 만드는 개발자입니다.\n\n추가 기능은 한 번만 구매하면 됩니다. 만년필·붓펜·수채 브러시 등 펜과 브러시 29종, 표지부터 속지 구조·간지·스티커까지 다른 스타일 100종(구매 전 전부 미리보기), PDF 주석, 페이지에 붙는 녹음, FSRS 암기카드.\n\n계정·광고 없음, 손글씨 인식과 검색은 기기에서 처리. 무료는 노트 1권(최대 5페이지)과 스타일 2종입니다. 인터페이스 50개 언어, 앱 안에서 전환."
 },
 {
  "app": "notesstudio100",
  "app_id": "6798813048",
  "lang": "en",
  "scenario": "英文：不要帳號、不要廣告、不送外部 AI 的手寫 App",
  "ct": "n100_us_private",
  "text": "A handwriting app with no account, no ads and no external AI reading your pages. That was the brief I gave myself for 100 Notes Studio (I'm the developer).\n\n29 pens and brushes. 100 notebook styles that differ in cover, paper and dividers, all previewable. PDF markup, audio attached to the page, on-device handwriting search, FSRS flashcards.\n\nFree: 1 notebook of up to 5 pages and 2 styles. The upgrade is a one-time purchase. Interface in 50 languages, switch in-app."
 }
]
```
