# TripBee Lite：四則情境貼文（app-posts.json 用）＋ Telegram 改寫與新增（tripbeelite-03）

| 項目 | 內容 |
|---|---|
| 用途 | ① 四則情境貼文，ct 依改善清單指定：`tbl_tw_trip`、`tbl_ja_shiori`、`tbl_ko_taiwan`、`tbl_vi_tet`，格式與 `.github/growth/app-posts.json` 的 posts 項目相同；② `telegram_posts.json` 裡 TripBee Lite（6791299610）只有 en、ja 兩則且文案抽象（calm、polished），這裡提供情境式替換稿，並新增 zh-Hant、ko、vi 三則。系列外宣連結全部指向 Lite |
| 發在哪／給誰 | ① threads-autopilot 排到店主本人的 Threads（zh-Hant、ja、ko），排在 2026 跨年與 2027 春節（2027-02-06）前 6 週，每週 1–2 則（見 tripbeelite-06）；vi 那則只在**事先取得版主同意**的在台越南社團由店主本人貼出；② Telegram 頻道 LumiApps2026 |
| 發文者 | 店主 Guan Feng Lai 本人（Threads／社團，第一人稱、寫明開發者）；Telegram 為 Lumi Studio 官方頻道 |
| 發文規則 | 每帳號每天 ≤3 則、21 天不重複、正文不放連結（放第一則留言或簡介）；社團一版一次、先讀版規並取得版主同意、不做有獎評論、不以任何東西交換評分。Telegram 每則一個連結（ct=telegram）。**本檔沒有修改 `app-posts.json` 或 `telegram_posts.json`**，由負責的人照 JSON 加入或替換 |
| 事實依據 | tripbeelite_full.json（en-US、zh-Hant、ja、ko、vi）：每日時間軸放航班、住宿、活動；備註、提醒、票券資訊；免費版一次存一趟、可隨時編輯或換成下一趟；一次購買非消耗型 Premium 永久解鎖無限旅程、旅程分享、完整備份與還原、智慧打包清單；無訂閱；不需帳號；無廣告、分析、追蹤。介面 50 種語言、App 內切換（店主確認） |
| 不能寫 | 「離線可用」（Lite 描述沒寫）；孩子年齡打包、第 X 天、Apple 地圖、天氣、海報、CSV（只在 Pro listing）；**免費版有打包清單**（打包清單在一次買斷內，返鄉打包那則要明說）；「calm／polished／精緻」這類抽象形容；兩人共用時暗示內容會翻譯（只有介面切換） |

---

## A. app-posts.json 新增四則

### A1. `tbl_tw_trip`（台灣 Threads：跨年／春節自由行，行程散落各處）

```json
{
  "app": "tripbeelite",
  "app_id": "6791299610",
  "lang": "zh-Hant",
  "scenario": "台灣 Threads：跨年／春節前 6 週，自由行行程散在訂房信、LINE、截圖（免費存一趟；打包清單在一次買斷內）",
  "ct": "tbl_tw_trip",
  "text": "跨年要去日本自由行，結果機票在信箱、飯店在訂房 App、景點門票在 LINE 群組的截圖裡。我做 TripBee Lite 就是為了這種「只差整理」的時候：一趟旅行一條每日時間軸，第一天幾點的航班、住哪間、晚上要吃什麼，一格一格排好，訂位編號和提醒就寫在旁邊。\n\n免費版可以存一趟，回來再換下一趟。要同時存好幾趟、分享給旅伴、完整備份，或用智慧打包清單，一次買斷就好，沒有訂閱。不用帳號、沒有廣告和追蹤。介面有 50 種語言，在 App 裡就能切換。"
}
```

### A2. `tbl_ja_shiori`（日本 Threads／X：年末年始の旅のしおり）

```json
{
  "app": "tripbeelite",
  "app_id": "6791299610",
  "lang": "ja",
  "scenario": "日本 Threads：年末年始の旅行前、旅のしおりを作る（無料で1件、持ち物リストは買い切り側）",
  "ct": "tbl_ja_shiori",
  "text": "年末年始の旅のしおり、今年はアプリで作ってみませんか。TripBee Lite は「いま準備している旅ひとつ」を日ごとのタイムラインにまとめるアプリです。1日目の便の時間、ホテル、夜のお店。メモ、リマインダー、チケット番号もその予定の横に置けます。\n\n無料版は旅を1件保存でき、帰ってきたら次の旅に入れ替え。何件も保存したいとき、同行者に共有したいとき、バックアップやスマート持ち物リストを使いたいときは、買い切りの Premium で解除できます。サブスクなし、アカウント不要、広告・トラッキングなし。表示言語は50言語、アプリ内で切り替えられます。台湾で個人開発しています。"
}
```

### A3. `tbl_ko_taiwan`（韓國 Threads：대만 여행 일정 정리）

```json
{
  "app": "tripbeelite",
  "app_id": "6791299610",
  "lang": "ko",
  "scenario": "韓國 Threads：準備台灣旅行，整理 대만 여행 일정표（開發者在台灣；免費存一趟）",
  "ct": "tbl_ko_taiwan",
  "text": "대만에서 앱을 만드는 개발자입니다. 한국에서 대만 여행 오시는 분들 일정표 보면 항공권은 메일, 숙소는 예약 앱, 야시장 리스트는 캡처에 흩어져 있는 경우가 많더라고요.\n\nTripBee Lite는 지금 준비하는 여행 하나를 날짜별 타임라인으로 정리하는 앱이에요. 첫날 항공편 시간, 숙소, 저녁 일정까지 순서대로 놓고 메모, 알림, 티켓 번호를 바로 옆에 적어 둘 수 있어요. 무료 버전은 여행 하나를 저장하고, 다녀오면 다음 여행으로 바꾸면 됩니다. 여행 무제한 저장, 공유, 전체 백업, 스마트 준비물 목록은 한 번 구매로 열려요. 구독 없음, 계정·광고·추적 없음. 표시 언어 50개, 앱 안에서 바꿀 수 있어요."
}
```

### A4. `tbl_vi_tet`（在台越南社群，經版主同意：Tết 2027 返鄉；打包清單要付費、明說）

```json
{
  "app": "tripbeelite",
  "app_id": "6791299610",
  "lang": "vi",
  "scenario": "在台越南新住民／移工社團（經版主同意）：2027 Tết（2/6）返鄉行程；打包清單在一次買斷內；共用 iPad 只切介面",
  "ct": "tbl_vi_tet",
  "text": "Mình là người làm ứng dụng TripBee Lite ở Đài Loan, xin phép admin chia sẻ.\n\nTết năm nay về quê, giờ bay, lịch đi thăm họ hàng, mã vé lại nằm rải rác trong tin nhắn? TripBee Lite xếp một chuyến đi theo từng ngày: chuyến bay, nơi ở, lịch hẹn, kèm ghi chú, lời nhắc và thông tin vé ngay bên cạnh. Bản miễn phí lưu được một chuyến.\n\nNói rõ để mọi người khỏi hiểu nhầm: danh sách đồ mang theo thông minh, lưu nhiều chuyến, chia sẻ và sao lưu nằm trong gói Premium mua một lần, không thuê bao. Không cần tài khoản, không quảng cáo. Giao diện có 50 ngôn ngữ, có tiếng Việt, đổi ngay trong ứng dụng; trên iPad dùng chung, mẹ để tiếng Việt, bố đổi sang tiếng Trung. Chỉ giao diện đổi ngôn ngữ, ghi chú bạn gõ không được dịch."
}
```

---

## B. Telegram（`telegram_posts.json`，app `6791299610`）

連結沿用：`https://apps.apple.com/app/id6791299610?pt=118326163&ct=telegram&mt=8`

### B1. 取代 en（原文：`🧳 TripBee Lite — Give one upcoming journey your full attention: a calm day-by-day planner for a single trip…`）

```json
{
  "lang": "en",
  "app": "6791299610",
  "text": "🧳 Booking emails, a group chat and a camera roll full of screenshots: that's most trip plans a week before departure. TripBee Lite turns the one trip you're about to take into a day-by-day timeline with flights, stays and activities, and keeps notes, reminders and ticket references beside them. Free for one journey at a time; a one-time Premium unlock adds unlimited journeys, sharing, full backup and restore and the smart packing list. No account, no ads, no tracking. 50 interface languages, switchable in the app.",
  "url": "https://apps.apple.com/app/id6791299610?pt=118326163&ct=telegram&mt=8"
}
```

### B2. 取代 ja（原文：`🧳 TripBee Lite — 次の1回の旅行に集中できる、静かな日別プランナー…`）

```json
{
  "lang": "ja",
  "app": "6791299610",
  "text": "🧳 旅のしおりを、スクショとメモから卒業させる。TripBee Lite は次の旅ひとつを日ごとのタイムラインに整理し、フライト・宿泊・予定の横にメモ、リマインダー、チケット情報を置けます。無料版は旅を1件保存。複数保存・共有・バックアップ・スマート持ち物リストは買い切りの Premium で、サブスクなし。アカウント不要、広告・トラッキングなし。表示言語は50言語、アプリ内で切り替え。",
  "url": "https://apps.apple.com/app/id6791299610?pt=118326163&ct=telegram&mt=8"
}
```

### B3. 新增 zh-Hant

```json
{
  "lang": "zh-Hant",
  "app": "6791299610",
  "text": "🧳 連假出國前一週，行程還散在訂房信、LINE 和截圖裡？【TripBee Lite】把這一趟排成每日時間軸：航班、住宿、活動一格一格放好，備註、提醒、票券編號就寫在旁邊。免費版存一趟，回來再換下一趟；想存多趟、分享給旅伴、完整備份或用智慧打包清單，一次買斷，沒有訂閱。不用帳號、沒有廣告和追蹤。介面 50 種語言，可在 App 內切換。",
  "url": "https://apps.apple.com/app/id6791299610?pt=118326163&ct=telegram&mt=8"
}
```

### B4. 新增 ko

```json
{
  "lang": "ko",
  "app": "6791299610",
  "text": "🧳 여행 일정표, 아직 캡처와 메모에 흩어져 있나요? TripBee Lite는 지금 준비하는 여행 하나를 날짜별 타임라인으로 정리해요. 항공편, 숙소, 일정 옆에 메모, 알림, 티켓 정보를 함께 보관하세요. 무료 버전은 여행 하나를 저장하고, 여행 무제한 저장·공유·전체 백업·스마트 준비물 목록은 한 번 구매로 열려요. 구독 없음, 계정·광고·추적 없음. 표시 언어 50개, 앱 안에서 변경 가능.",
  "url": "https://apps.apple.com/app/id6791299610?pt=118326163&ct=telegram&mt=8"
}
```

### B5. 新增 vi

```json
{
  "lang": "vi",
  "app": "6791299610",
  "text": "🧳 Chuẩn bị về quê ăn Tết: giờ bay, nơi ở, lịch thăm họ hàng và mã vé nằm rải rác khắp nơi? TripBee Lite xếp một chuyến đi theo từng ngày, có ghi chú, lời nhắc và thông tin vé ngay bên cạnh. Bản miễn phí lưu một chuyến; danh sách đồ mang theo thông minh, lưu nhiều chuyến, chia sẻ và sao lưu mở bằng một lần mua, không thuê bao. Không cần tài khoản, không quảng cáo. Giao diện 50 ngôn ngữ, có tiếng Việt, đổi ngay trong ứng dụng.",
  "url": "https://apps.apple.com/app/id6791299610?pt=118326163&ct=telegram&mt=8"
}
```

---

## 加入／替換後檢查

- [ ] 四則 `ct` 與改善清單一致：`tbl_tw_trip`、`tbl_ja_shiori`、`tbl_ko_taiwan`、`tbl_vi_tet`；第一則留言連結 `https://apps.apple.com/app/id6791299610?pt=118326163&ct={ct}&mt=8`
- [ ] 這四則和 app-posts.json 既有的 `tripbeelite_zhHant_1`、`tripbeelite_ja_2`、`tripbeelite_ko_3`、`tripbeelite_vi_4` 情境相近：同一帳號兩則之間至少隔 21 天，或擇一使用
- [ ] 沒有任何一則說 Lite 離線、有 Apple 地圖或孩子年齡打包
- [ ] 打包清單每次出現都在「一次買斷／Premium」那句裡
- [ ] Telegram 每則只有一個 url
