# Snapport Lite：四則情境貼文（app-posts.json 用）＋ Telegram 改寫與新增（snapportlite-05）

| 項目 | 內容 |
|---|---|
| 用途 | ① 四則情境貼文，ct 依改善清單指定：`spl_tw_online`、`spl_ja_online`、`spl_id_job`、`spl_vi_doc`，格式與 `.github/growth/app-posts.json` 的 posts 項目相同，可直接加入陣列；② `telegram_posts.json` 裡 Snapport Lite（6792856304）現有 en、ja 兩則是抽象文案，這裡提供情境式替換稿，並新增 zh-Hant、id、vi 三則 |
| 發在哪／給誰 | ① 由 threads-autopilot 排程到店主本人的 Threads（zh-Hant、ja），id／vi 兩則只在**事先取得版主同意**的在台印尼／越南社團由店主本人貼出（見 snapportlite-08）；② Telegram 頻道 LumiApps2026（telegram-daily 自動發文） |
| 發文者 | 店主 Guan Feng Lai 本人（Threads／社團，文中第一人稱已寫明是開發者）；Telegram 為 Lumi Studio 官方頻道（店主經營） |
| 發文規則 | 每帳號每天 ≤3 則、同一則 21 天內不重發、正文不放連結（連結放第一則留言或簡介）；社團貼文一版一次、先讀版規並取得版主同意、不做有獎評論、不以任何東西交換評分。Telegram 每則一個連結（ct=telegram）。**本檔沒有修改 `app-posts.json` 或 `telegram_posts.json`**，由負責這兩個檔案的人（本機 Claude／店主）照下方 JSON 加入或替換 |
| 事實依據 | snapportlite_full.json（en-US、zh-Hant、ja、id、vi）：35 種範本含 2×2 英吋、35×45 公釐；自訂尺寸 mm／inch／pixel 與 DPI；裝置上臉部偵測＋頭頂／眼睛／下巴導引線；保留原背景或換白、淺灰、藍、紅、自訂色；亮度／對比／色溫／銳利度輕微調整；匯出 JPEG／PNG／PDF；4×6 英吋、A4、Letter 排版、一頁多張、裁切線；照片在裝置上處理不上傳、可離線；範本與編修免費、第一次匯出免費、一次購買不限次數匯出，無訂閱／廣告／追蹤／帳號；不保證受理、不隸屬政府。介面 50 種語言、App 內切換（店主確認）。台灣線上申換條件與電子檔規格：領事事務局專區與系統常見問答（見 guide-online-passport-renewal-photo-zh-hant.md 的出處）；日本 600×730px／600KB：マイナポータル FAQ（見 note-com-online-shinsei-kaoshashin-check-ja.md） |
| 不能寫 | 「退件主因是照片」這類無官方統計的說法；保證受理；美肌；「44 種語言」（listing 舊字，介面以店主確認的 50 為準）；3×4、4×6 公分是內建範本（listing 只列 2×2 in、35×45、33×48、50×70 mm，其他尺寸一律寫「自訂尺寸」）；一張紙排不同尺寸（listing 只寫一頁多張） |
| 名稱 | 線上名稱：TW「Snapport Lite：在家拍證件照」、JP「Snapport Lite：自宅で証明写真」、US「Snapport Lite: Take ID Photos」。id／vi 店面目前名稱為「Snapport Lite」 |

> 印尼文、越南文兩則提到的「4×6」有兩種意思：照片尺寸 4×6 公分（當地證件照常用），以及沖印紙 4×6 英吋（印尼常稱 4R、越南常稱 10x15）。文中已分開寫清楚，替換時不要合併成同一個「4x6」。

---

## A. app-posts.json 新增四則

### A1. `spl_tw_online`（台灣 Threads：線上申換護照）

```json
{
  "app": "snapportlite",
  "app_id": "6792856304",
  "lang": "zh-Hant",
  "scenario": "台灣 Threads：護照快到期、符合線上申換條件、照片要自己上傳（只寫官方條件與規格；強調鏡像與不修圖；不保證受理）",
  "ct": "spl_tw_online",
  "text": "護照明年到期，才發現 7 月起線上申換放寬了：在台有戶籍的成年人、護照已過期或效期不足 1 年、資料不變更，用自然人憑證就能在網路上申請。照片要自己上傳，領事局特別寫了鏡像（左右相反）、合成、修圖過度的照片要重新申辦，所以我的建議是請家人用後鏡頭、對著真的白牆拍，不換底、不修圖。\n\n我做的 Snapport Lite 只負責最後一步：裁成 35×45mm、用頭頂／眼睛／下巴導引線對位、匯出 JPG（系統要求至少 413×531 像素、5MB 以內）。範本和編修免費，第一次匯出也免費；照片只在手機上處理，不上傳。App 不保證受理，送件前請先看領事局線上申換專區。"
}
```

### A2. `spl_ja_online`（日本 Threads／note 告知：オンライン申請の顔写真）

```json
{
  "app": "snapportlite",
  "app_id": "6792856304",
  "lang": "ja",
  "scenario": "日本 Threads：マイナポータルでパスポートをオンライン申請、写真を自分で用意する（左右反転の注意、マイナポータルのカメラも選択肢として明記）",
  "ct": "spl_ja_online",
  "text": "パスポートのオンライン申請で、各県の案内がいちばん注意しているのは「左右反転」。インカメラの自撮りは反転することがあるので、家族に背面カメラで撮ってもらうか、マイナポータルのカメラでその場で撮るのが確実です。\n\n自分の画像を使うなら、FAQ の規格（JPG・横600×縦730px・600KB以内、最新は要確認）に合わせて切り抜きます。私が作っている Snapport Lite は、端末上で頭頂・目・あごのガイド線に合わせてピクセル指定で切り抜けます。テンプレートと編集は無料、最初の書き出しも無料。写真はアップロードされません。受理は保証できないので、申請先の案内を必ず確認してください。"
}
```

### A3. `spl_id_job`（在台印尼社群，經版主同意：求職／辦文件要 pas foto）

```json
{
  "app": "snapportlite",
  "app_id": "6792856304",
  "lang": "id",
  "scenario": "在台印尼移工社團（經版主同意）：求職或辦文件要 pas foto 3x4／4x6 cm 紅藍底；3x4、4x6 cm 用自訂尺寸；沖印紙 4R＝4×6 英吋",
  "ct": "spl_id_job",
  "text": "Saya pembuat aplikasi Snapport Lite, izin berbagi setelah dapat persetujuan admin.\n\nMau melamar kerja atau urus dokumen, lalu diminta pas foto 3x4 cm latar merah atau 4x6 cm latar biru? Di Snapport Lite, ukuran bisa diatur sendiri dalam mm (30×40 atau 40×60), wajah disejajarkan dengan garis puncak kepala, mata, dan dagu, lalu latar diganti ke merah, biru, atau putih. Hasilnya bisa disusun beberapa lembar di kertas 4R (4×6 inci) atau A4 dengan garis potong, jadi cukup cetak satu lembar.\n\nTemplate dan edit gratis, ekspor pertama gratis; ekspor tanpa batas cukup sekali beli, tanpa langganan. Foto diproses di HP, tidak diunggah. Tampilan aplikasi tersedia dalam 50 bahasa, termasuk Bahasa Indonesia, dan bisa diganti di dalam aplikasi. Aturan foto tiap instansi berbeda, jadi cek dulu syaratnya."
}
```

### A4. `spl_vi_doc`（在台越南社群，經版主同意：辦文件要 ảnh thẻ）

```json
{
  "app": "snapportlite",
  "app_id": "6792856304",
  "lang": "vi",
  "scenario": "在台越南新住民／移工社團（經版主同意）：辦文件臨時要 ảnh thẻ 3x4／4x6 cm；自訂尺寸；沖印紙 10x15＝4×6 英吋；只切介面",
  "ct": "spl_vi_doc",
  "text": "Mình là người làm ứng dụng Snapport Lite, xin phép admin chia sẻ.\n\nĐang làm hồ sơ thì được yêu cầu ảnh thẻ 3x4 hay 4x6 cm? Với Snapport Lite, bạn đặt kích thước theo mm (30×40 hoặc 40×60), căn khuôn mặt theo đường đỉnh đầu, mắt và cằm, đổi nền trắng, xanh hoặc đỏ, rồi xếp nhiều ảnh trên một tờ 10x15 (4×6 inch) hoặc A4 có đường cắt để mang đi in một lần.\n\nMẫu và chỉnh sửa miễn phí, lần xuất đầu tiên miễn phí; muốn xuất không giới hạn thì mua một lần, không thuê bao. Ảnh được xử lý trên điện thoại, không tải lên. Giao diện có 50 ngôn ngữ, có tiếng Việt, đổi ngay trong ứng dụng (chỉ đổi giao diện, không dịch chữ bạn gõ). Mỗi cơ quan có quy định ảnh khác nhau, nhớ kiểm tra trước khi nộp."
}
```

---

## B. Telegram（`telegram_posts.json`，app `6792856304`）

連結一律沿用既有格式：`https://apps.apple.com/app/id6792856304?pt=118326163&ct=telegram&mt=8`

### B1. 取代 en（原文：`🪪 Snapport Lite — Passport, visa and ID photos at home with guided sizing and print-ready sheets. Free to start, one-time unlock.`）

```json
{
  "lang": "en",
  "app": "6792856304",
  "text": "🪪 Renewing a passport online and asked to upload your own photo? Snapport Lite crops it to 2×2 in or 35×45 mm on your iPhone, with head-top, eye-line and chin guides. Keep your real white-wall background, export a JPEG, or lay out a 4×6 in print sheet with cut guides. Every preset and edit is free, and so is your first export; a one-time unlock gives unlimited exports. Photos never leave the device. 50 interface languages, switchable in the app. It can't guarantee acceptance, so check the official photo rules first.",
  "url": "https://apps.apple.com/app/id6792856304?pt=118326163&ct=telegram&mt=8"
}
```

### B2. 取代 ja（原文：`🪪 Snapport Lite — パスポート・ビザ・証明写真を自宅で。サイズガイドと印刷用シート付き。無料開始、買い切り。`）

```json
{
  "lang": "ja",
  "app": "6792856304",
  "text": "🪪 パスポートのオンライン申請、写真を自分で用意するなら「左右反転」に注意。家族に背面カメラで撮ってもらうのが確実です。Snapport Lite（自宅で証明写真）は端末上で頭頂・目・あごのガイド線に合わせ、mm やピクセル指定でぴったり切り抜き。元の背景を残したまま JPEG で書き出せます。テンプレートと編集は無料、最初の書き出しも無料、写真はアップロードされません。表示言語は50言語からアプリ内で切り替え。受理は保証されないので、申請先の規定を確認してください。",
  "url": "https://apps.apple.com/app/id6792856304?pt=118326163&ct=telegram&mt=8"
}
```

### B3. 新增 zh-Hant

```json
{
  "lang": "zh-Hant",
  "app": "6792856304",
  "text": "🪪 線上申換護照要自己上傳照片？【Snapport Lite：在家拍證件照】在手機上把照片裁成 35×45mm，用頭頂、眼睛、下巴導引線對位，保留真的白牆背景，匯出 JPG。小提醒：請家人用後鏡頭拍，避免鏡像；不要修圖。所有範本與編修免費、第一次匯出免費，之後一次買斷不限次數。照片不上傳。介面 50 種語言，可在 App 內切換。不保證受理，送件前請看領事局規定。",
  "url": "https://apps.apple.com/app/id6792856304?pt=118326163&ct=telegram&mt=8"
}
```

### B4. 新增 id

```json
{
  "lang": "id",
  "app": "6792856304",
  "text": "🪪 Butuh pas foto 3x4 cm latar merah atau 4x6 cm latar biru untuk lamaran kerja? Snapport Lite memotong foto sesuai ukuran mm yang Anda atur, dengan garis panduan kepala, mata, dan dagu, lalu mengganti latar ke merah, biru, atau putih. Susun beberapa foto di kertas 4R (4×6 inci) atau A4 dengan garis potong. Template dan edit gratis, ekspor pertama gratis. Foto tidak diunggah. Tampilan 50 bahasa, termasuk Bahasa Indonesia, diganti di dalam aplikasi. Cek dulu aturan foto instansi.",
  "url": "https://apps.apple.com/app/id6792856304?pt=118326163&ct=telegram&mt=8"
}
```

### B5. 新增 vi

```json
{
  "lang": "vi",
  "app": "6792856304",
  "text": "🪪 Cần ảnh thẻ 3x4 hoặc 4x6 cm để làm hồ sơ? Snapport Lite cắt ảnh theo kích thước mm bạn đặt, có đường căn đỉnh đầu, mắt, cằm; đổi nền trắng, xanh hoặc đỏ; xếp nhiều ảnh trên tờ 10x15 (4×6 inch) hoặc A4 có đường cắt. Mẫu và chỉnh sửa miễn phí, lần xuất đầu miễn phí. Ảnh không tải lên. Giao diện 50 ngôn ngữ, có tiếng Việt, đổi ngay trong ứng dụng. Hãy kiểm tra quy định ảnh của cơ quan trước khi nộp.",
  "url": "https://apps.apple.com/app/id6792856304?pt=118326163&ct=telegram&mt=8"
}
```

---

## 加入／替換後檢查

- [ ] app-posts.json 四則的 `ct` 與改善清單一致：`spl_tw_online`、`spl_ja_online`、`spl_id_job`、`spl_vi_doc`；第一則留言的連結用 `https://apps.apple.com/app/id6792856304?pt=118326163&ct={ct}&mt=8`
- [ ] 6792856304 的 Telegram 貼文裡沒有「44 languages」、沒有「保證」、沒有「美肌」
- [ ] 3x4／4x6 cm 都寫成自訂尺寸（mm），沒有說是內建範本
- [ ] id、vi 兩則的社團發文前已取得版主同意，且只發一次
- [ ] 每則 Telegram 只有一個 url
