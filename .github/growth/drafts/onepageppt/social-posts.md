# OnePage PPT：四語貼文（onepageppt-02）

| 項目 | 內容 |
|---|---|
| 用途 | 把外宣從「AI Slide Maker／資料作成」這類搶不到的大詞，轉到「一頁簡報／1枚資料／한 장 보고서／one-pager」需求；搭配 15 秒前後對照影片與成品截圖 |
| 平台／對象 | zh-Hant：Threads；ja：Threads／note 的つぶやき；ko：Threads／Instagram；en：LinkedIn／Threads。對象：被要求交「一頁」的上班族、PM、顧問、學生 |
| 發文者 | 店主 Guan Feng Lai，用**本人帳號**，正文已寫明開發者身分 |
| 發文規則 | 每帳號每天最多 3 則、同一則 21 天內不重發；正文不放連結，連結放第一則留言或簡介；附圖只用 App 真實成品（素材在 `demo/`，要保留「虛構示範」字樣）；不寫排名用語、不比較他牌 |
| 免費額度寫法 | zh-Hant 照 live「可以先免費做一張」；ja／ko／en 照 live 不寫張數（「無料で試せます」「무료로 먼저 써 보세요」「Try it free」）。資料檔 `onepageppt_full.json` 仍寫「幾張」，已過時 |
| 事實依據 | 商店文案（2026-10-13 lookup，US／TW／JP／KR）；介面 50 種語言、App 內切換（店主確認） |

> `app-posts.json` 已有第一輪（ct=`onepageppt_*`）；本檔是第二輪，ct 依 onepageppt-02 指定的 `opp_*` 命名。

---

### 台灣：一頁報告最難的是決定不放什麼
- lang: zh-Hant
- ct: opp_tw_onepage
- 平台: Threads
- 連結（放第一則留言）: https://apps.apple.com/app/id6798814385?pt=118326163&ct=opp_tw_onepage&mt=8

```text
「一頁報告」最難的不是排版，是決定哪些不放。

我做 OnePage PPT 時給它的規則是：貼上會議紀錄、截圖、PDF 或 CSV，它把重點整理成標題，數字變圖表、日期變時間軸、步驟變流程圖；資料撐不住就不畫，也不編數字。不滿意就一鍵改版，有六種方向，喜歡的元素可以鎖住。

匯出可編輯的 pptx、PDF、PNG，同事拿到還能改。全程在裝置上處理、不用帳號。可以先免費做一張，Lifetime Pro 一次購買。介面 50 種語言，App 內切換。（我是開發者）
```

### 日本：ワンペーパーで、と言われたら
- lang: ja
- ct: opp_jp_1mai
- 平台: Threads
- 連結（放第一則留言）: https://apps.apple.com/app/id6798814385?pt=118326163&ct=opp_jp_1mai&mt=8

```text
「ワンペーパーで」と言われたとき、いちばん時間がかかるのは、何を載せないかを決めることかもしれません。

OnePage PPT（開発者です）は、メモ・スクショ・PDF・CSVから要点を見出しにして、16:9のスライド1枚に組みます。数字はグラフ、日付は年表、手順はフロー図に。データが裏づけない図は描かず、数字も作りません。6種類のワンタップ再デザイン、気に入った要素はロック。

編集できるpptx・PDF・PNGで書き出し。端末内処理・アカウント不要。無料で試せて、Lifetime Proは買い切り。表示言語は50種類、アプリ内で切替可。
```

### 韓國：한 장 보고서，先決定要刪什麼
- lang: ko
- ct: opp_kr_hanjang
- 平台: Threads／Instagram
- 連結（放第一則留言或簡介）: https://apps.apple.com/app/id6798814385?pt=118326163&ct=opp_kr_hanjang&mt=8

```text
한 장 보고서에서 제일 오래 걸리는 건 '무엇을 뺄지' 정하는 일입니다.

OnePage PPT(제가 만든 앱입니다)는 메모, 캡처, PDF, CSV에서 핵심을 제목으로 뽑아 16:9 슬라이드 한 장으로 정리합니다. 숫자는 차트로, 날짜는 타임라인으로, 절차는 흐름도로. 데이터가 뒷받침하지 않으면 차트를 그리지 않고 숫자도 지어내지 않습니다. 리디자인 6종, 마음에 드는 요소는 잠금.

편집 가능한 pptx·PDF·PNG로 내보내기. 기기 안에서 처리, 계정 불필요. 무료로 먼저 써 보고, Lifetime Pro는 한 번만 결제. 인터페이스 50개 언어, 앱 안에서 전환.
```

### 英文：one-pager 最難的是取捨
- lang: en
- ct: opp_us_onepager
- 平台: LinkedIn／Threads
- 連結（放第一則留言）: https://apps.apple.com/app/id6798814385?pt=118326163&ct=opp_us_onepager&mt=8

```text
The hardest part of a one-pager is deciding what to leave out.

OnePage PPT (I'm the developer) turns notes, screenshots, a PDF or a CSV into one 16:9 slide: headlines, a chart, a timeline or a process flow. No chart if the data can't support one, and no invented figures. Six one-tap redesigns; lock what you like.

Export editable .pptx, PDF or PNG. On-device, no account, works offline. Try it free; Lifetime Pro is one purchase. 50 interface languages, switchable in-app.
```

## 給本機 Claude：併入 app-posts.json 的條目

這次雲端工作只能寫 `drafts/`，所以沒有動 `app-posts.json`。本機 Claude 審過後，可把下列物件直接加進 `posts` 陣列（`ct` 都是新的，不與第一輪重複）。

| ct | lang | 字元數（Threads 上限 500） |
|---|---|---|
| opp_tw_onepage | zh-Hant | 233 |
| opp_jp_1mai | ja | 273 |
| opp_kr_hanjang | ko | 323 |
| opp_us_onepager | en | 475 |

```json
[
 {
  "app": "onepageppt",
  "app_id": "6798814385",
  "lang": "zh-Hant",
  "scenario": "台灣：一頁報告最難的是決定不放什麼",
  "ct": "opp_tw_onepage",
  "text": "「一頁報告」最難的不是排版，是決定哪些不放。\n\n我做 OnePage PPT 時給它的規則是：貼上會議紀錄、截圖、PDF 或 CSV，它把重點整理成標題，數字變圖表、日期變時間軸、步驟變流程圖；資料撐不住就不畫，也不編數字。不滿意就一鍵改版，有六種方向，喜歡的元素可以鎖住。\n\n匯出可編輯的 pptx、PDF、PNG，同事拿到還能改。全程在裝置上處理、不用帳號。可以先免費做一張，Lifetime Pro 一次購買。介面 50 種語言，App 內切換。（我是開發者）"
 },
 {
  "app": "onepageppt",
  "app_id": "6798814385",
  "lang": "ja",
  "scenario": "日本：ワンペーパーで、と言われたら",
  "ct": "opp_jp_1mai",
  "text": "「ワンペーパーで」と言われたとき、いちばん時間がかかるのは、何を載せないかを決めることかもしれません。\n\nOnePage PPT（開発者です）は、メモ・スクショ・PDF・CSVから要点を見出しにして、16:9のスライド1枚に組みます。数字はグラフ、日付は年表、手順はフロー図に。データが裏づけない図は描かず、数字も作りません。6種類のワンタップ再デザイン、気に入った要素はロック。\n\n編集できるpptx・PDF・PNGで書き出し。端末内処理・アカウント不要。無料で試せて、Lifetime Proは買い切り。表示言語は50種類、アプリ内で切替可。"
 },
 {
  "app": "onepageppt",
  "app_id": "6798814385",
  "lang": "ko",
  "scenario": "韓國：한 장 보고서，先決定要刪什麼",
  "ct": "opp_kr_hanjang",
  "text": "한 장 보고서에서 제일 오래 걸리는 건 '무엇을 뺄지' 정하는 일입니다.\n\nOnePage PPT(제가 만든 앱입니다)는 메모, 캡처, PDF, CSV에서 핵심을 제목으로 뽑아 16:9 슬라이드 한 장으로 정리합니다. 숫자는 차트로, 날짜는 타임라인으로, 절차는 흐름도로. 데이터가 뒷받침하지 않으면 차트를 그리지 않고 숫자도 지어내지 않습니다. 리디자인 6종, 마음에 드는 요소는 잠금.\n\n편집 가능한 pptx·PDF·PNG로 내보내기. 기기 안에서 처리, 계정 불필요. 무료로 먼저 써 보고, Lifetime Pro는 한 번만 결제. 인터페이스 50개 언어, 앱 안에서 전환."
 },
 {
  "app": "onepageppt",
  "app_id": "6798814385",
  "lang": "en",
  "scenario": "英文：one-pager 最難的是取捨",
  "ct": "opp_us_onepager",
  "text": "The hardest part of a one-pager is deciding what to leave out.\n\nOnePage PPT (I'm the developer) turns notes, screenshots, a PDF or a CSV into one 16:9 slide: headlines, a chart, a timeline or a process flow. No chart if the data can't support one, and no invented figures. Six one-tap redesigns; lock what you like.\n\nExport editable .pptx, PDF or PNG. On-device, no account, works offline. Try it free; Lifetime Pro is one purchase. 50 interface languages, switchable in-app."
 }
]
```
