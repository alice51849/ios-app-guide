# DailyMate Lite：三則看護情境貼文（app-posts.json 用）＋ Telegram 兩則改寫（dailymatelite-04）

| 項目 | 內容 |
|---|---|
| 用途 | ① 三則看護情境貼文，ct 依改善清單：`dml_tw_care`、`dml_id_care`、`dml_vi_care`，格式與 `.github/growth/app-posts.json` 的 posts 項目相同，可直接加入；② `telegram_posts.json` 裡 DailyMate Lite（6794725568）的 en、ja 兩則（索引 205、206）改成情境式 |
| 發在哪／給誰 | ① `dml_tw_care`：threads-autopilot 排到店主本人 Threads，每週最多 1 則、不帶連結（dailymatelite-07）；`dml_id_care`、`dml_vi_care`：只在**事先取得版主同意**的在台印尼／越南社團，或 One-Forty、新住民家庭服務中心同意轉發的管道，由店主本人貼出（dailymatelite-03）；② Telegram 頻道 LumiApps2026 |
| 發文者 | 店主 Guan Feng Lai 本人（第一人稱、寫明開發者）；Telegram 為 Lumi Studio 官方頻道 |
| 發文規則 | 每帳號每天 ≤3 則、21 天不重複、正文不放連結（放第一則留言）；社團一版一次、先讀版規並取得版主同意、不做有獎評論、不以任何東西交換評分。**本檔沒有修改 `app-posts.json` 或 `telegram_posts.json`**，由負責的人照 JSON 加入或替換 |
| ⚠ 發布前必做 | 店主在 App 內確認：學習語言清單裡有**中文**（並確認是繁體字還是簡體字、是否為台灣用語）、**印尼文**、**越南文**。三者任一不在，就不要發對應那則。若中文內容是簡體字，`dml_id_care`、`dml_vi_care` 要加一句「中文內容為簡體字」 |
| 事實依據 | dailymatelite_full.json（en-US、zh-Hant、id、vi、ja）：8,400 組提示與回覆；50 種學習語言；14 大主題、84 個情境（描述舉例：旅行、工作、餐飲、健康）；初級／中級／高級；裝置內建系統語音、可調語速；各語言進度、連續天數、收藏分開保存；任何學習語言都能免費練「旅行」主題初級，其他主題可看真實預覽；一次性購買解鎖全部主題、三級、完整 8,400 組、無限收藏、互動小工具、Apple Watch、App Intents；無訂閱；無帳號、第三方廣告、分析、追蹤；切換語言、主題、級別不會失去進度。介面 50 種語言、App 內切換（店主確認） |
| 誠實規則 | 兩人共用一支手機時，**只有介面切換語言，輸入的文字不會被翻譯**——每則都寫。免費只有「旅行」初級，看護需要的「健康」「工作」主題在一次買斷內——每則都寫。不暗示這是專業看護訓練或語言檢定教材 |
| 不能寫 | 「保證學會」；看護專用課程；翻譯功能；免費層含健康／工作主題；其他語言 App 名稱；任何排名 |

---

## A. app-posts.json 新增三則

### A1. `dml_tw_care`（台灣 Threads：雇主家庭與看護共用一支手機）

```json
{
  "app": "dailymatelite",
  "app_id": "6794725568",
  "lang": "zh-Hant",
  "scenario": "台灣 Threads：雇主家庭想用看護的母語說幾句、看護想練中文，共用一支手機（發布前確認學習語言含中文、印尼文、越南文；只切介面；免費只有旅行初級）",
  "ct": "dml_tw_care",
  "text": "家裡請了印尼看護，阿嬤最想學的一句是「謝謝妳」，看護最想學的是「哪裡不舒服？」。兩個人用同一支手機，其實可以各學各的。\n\n我做的 DailyMate Lite 是一來一往的情境短句：一句提示配一句自然回覆，用手機內建語音聽發音、可以調慢。每種學習語言的進度和收藏分開記，所以看護把介面切成印尼文練中文、家人切回中文學印尼文，不會互相蓋掉。介面 50 種語言在 App 裡就能切換。\n\n要說清楚兩件事：只有介面會換語言，打的字不會被翻譯；免費的是「旅行」主題初級，健康、工作這些主題要一次買斷，沒有訂閱。不用帳號、沒有廣告。"
}
```

### A2. `dml_id_care`（在台印尼看護社群，經版主同意：練中文）

```json
{
  "app": "dailymatelite",
  "app_id": "6794725568",
  "lang": "id",
  "scenario": "在台印尼移工／看護社團（經版主同意）：用印尼文介面練中文；免費只有 Pelancong 初級；只切介面",
  "ct": "dml_id_care",
  "text": "Saya pembuat aplikasi DailyMate Lite, izin berbagi setelah dapat persetujuan admin.\n\nMau latihan bahasa Mandarin untuk ngobrol dengan Ama atau keluarga majikan? DailyMate Lite melatih percakapan lewat pasangan kalimat: satu kalimat pembuka dan balasan alaminya, dengan suara sistem di HP yang kecepatannya bisa diatur. Tampilan aplikasi bisa diganti ke Bahasa Indonesia di dalam aplikasi (ada 50 bahasa tampilan), jadi menu mudah dibaca sambil belajar Mandarin.\n\nKalau HP dipakai bersama keluarga majikan, kemajuan dan kalimat tersimpan dicatat terpisah untuk tiap bahasa. Hanya tampilan yang berganti bahasa; kalimat yang diketik tidak diterjemahkan.\n\nGratis: topik Pelancong tingkat Pemula. Topik lain seperti kesehatan dan pekerjaan dibuka dengan sekali beli, tanpa langganan. Tanpa akun, tanpa iklan."
}
```

### A3. `dml_vi_care`（在台越南看護／新住民社群，經版主同意：練中文、家人學越南文）

```json
{
  "app": "dailymatelite",
  "app_id": "6794725568",
  "lang": "vi",
  "scenario": "在台越南看護／新住民社團（經版主同意）：用越南文介面練中文，家人學越南文；免費只有 Du lịch 初級；只切介面",
  "ct": "dml_vi_care",
  "text": "Mình là người làm ứng dụng DailyMate Lite, xin phép admin chia sẻ.\n\nĐi làm chăm sóc người già ở Đài Loan, muốn nói được câu \"Bác thấy khó chịu ở đâu?\" bằng tiếng Trung? DailyMate Lite luyện theo cặp gợi ý – câu đáp: nghe bằng giọng đọc hệ thống trên điện thoại, chỉnh được tốc độ. Giao diện có 50 ngôn ngữ, có tiếng Việt, đổi ngay trong ứng dụng.\n\nNếu dùng chung điện thoại với gia đình chủ, tiến độ và câu đã lưu của mỗi ngôn ngữ được tách riêng: bạn học tiếng Trung, người nhà học tiếng Việt. Chỉ giao diện đổi ngôn ngữ, chữ bạn gõ không được dịch.\n\nMiễn phí: chủ đề Du lịch cấp cơ bản. Các chủ đề như sức khỏe, công việc mở bằng một lần mua, không thuê bao. Không cần tài khoản, không quảng cáo."
}
```

> `dml_vi_care` 引號內那句「Bác thấy khó chịu ở đâu?」是貼文自己的例句，不代表 App 內容一定有這句；若店主想改成 App 裡實際有的例句，請照 App 畫面替換。`dml_tw_care` 的「謝謝妳」「哪裡不舒服？」同理。

---

## B. Telegram（`telegram_posts.json`，app `6794725568`）

連結沿用：`https://apps.apple.com/app/id6794725568?pt=118326163&ct=telegram&mt=8`

### B1. 索引 205，取代 en（原文：`💬 DailyMate Lite — Be ready when it is your turn to speak: real situational sentences for travel. Free to start, one-time unlock.`）

```json
{
  "lang": "en",
  "app": "6794725568",
  "text": "💬 One shared iPhone, two learners: the caregiver practices the family's language, the family practices hers. DailyMate Lite keeps progress, streaks and saved phrases separate for every learning language, so nobody overwrites anybody. Short cue-and-reply cards, 50 learning languages, on-device system voices with adjustable speed. The interface switches between 50 languages inside the app; only the interface changes, typed text isn't translated. Traveler at Beginner level is free in any language; one purchase unlocks every topic and level. No subscription, no account, no ads.",
  "url": "https://apps.apple.com/app/id6794725568?pt=118326163&ct=telegram&mt=8"
}
```

### B2. 索引 206，取代 ja（原文：`💬 DailyMate Lite — 自分の番が来ても大丈夫。旅で使う場面別の完全な文を練習。無料開始、買い切り。`）

```json
{
  "lang": "ja",
  "app": "6794725568",
  "text": "💬 職場の同僚の母語で、ひとことあいさつしてみたい。DailyMate Lite は学習言語50から選べて、「問いかけ」と「自然な返答」のペアで一往復を練習します。端末のシステム音声で発音を確認、速度も調整可能。言語ごとに進捗とお気に入りが分かれるので、いくつ並行しても大丈夫。どの言語でも「旅行」初級は無料、残りは買い切りで解除。表示言語も50言語からアプリ内で切り替えられます。アカウント不要、広告なし。",
  "url": "https://apps.apple.com/app/id6794725568?pt=118326163&ct=telegram&mt=8"
}
```

---

## 加入／替換後檢查

- [ ] 已在 App 內確認學習語言含中文（繁／簡）、印尼文、越南文
- [ ] 三則 `ct` 與改善清單一致：`dml_tw_care`、`dml_id_care`、`dml_vi_care`；留言連結 `https://apps.apple.com/app/id6794725568?pt=118326163&ct={ct}&mt=8`
- [ ] 和 app-posts.json 既有的 `dailymatelit_zhHant_1`、`dailymatelit_id_2`、`dailymatelit_vi_3` 情境相近：同帳號同社團至少隔 21 天，或擇一使用
- [ ] 每則都有「只切介面、不翻譯」與「免費只有旅行初級」
- [ ] Telegram 每則只有一個 url
