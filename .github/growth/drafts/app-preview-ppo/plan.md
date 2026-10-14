# App Preview × 產品頁 A/B（PPO）計畫：Mochi、BattAI、Cyca

> 狀態：**草案，等 Caitlyn 看樣片並核准**（2026-10-14）。
>
> 這份計畫沒有對 App Store Connect 做任何讀寫。建立測試、上傳影片、送審、啟動，都要等她核准後由本機 session 執行。

## 1. 選哪三款、為什麼

資料來源：
- 00_GrowthEngine `reports/funnel-latest.json`，其中營收截至 10-14，ASC Analytics 是 10-07 的 30 天快照；
- ios-app-guide `.github/growth/performance.json` 還不存在。`clip-posts.json` 有 0 筆，所以**還沒有任何鉤子成效資料**。

| App | 30 天下載 | 曝光 | 產品頁瀏覽 | 首次下載／曝光 | 為什麼選 |
|---|---|---|---|---|---|
| Mochi（6785004775） | 2,573 | 79,958 | 7,082 | 3.5% | 全公司第一，下載和營收（US$434）都是。有分鏡、鉤子片、50 語商店截圖 |
| BattAI（6802423998） | 372 | 11,237 | 1,209 | 3.0% | 下載第二、產品頁瀏覽第二。截圖是真實 App 畫面，有 zh-Hant／ja／ko 在地化截圖 |
| Cyca（6782251621） | 195 | 15,262 | 563 | 1.4% | 下載第三、曝光第二。轉換率最低，所以進步空間最大。截圖是真實 App 畫面，有 6 語截圖 |

**排除的 App：**
- ledmovingtext、studydown：HOLD。
- 付費版：snapport、wordmate、zipbox、gmoney、lumibopomofopro、wifiaid、dailymate、tripbee、hourstag、lumiletterspro、lumimathpro、lumimissionpro。
- Lumi Weather：下載 158，排第四，當候補。
- stayclock：沒有 ASC Analytics 資料，無法評估。

## 2. Apple 規格與審核（2026-10-14 查官方文件）

**技術規格：**
- 長度 15–30 秒。第二版做 **15.5 秒**：短一點節奏比較緊，又留了 0.5 秒緩衝不會低於下限。
- 6.9 吋 iPhone 直式 **886×1920**：已確認。6.5 吋和 6.1 吋也接受同一個尺寸。
- 最高 30 fps，H.264 High Profile 最高 Level 4.0，目標位元率 10–12 Mbps。
- 立體聲 AAC 256 kbps，44.1 或 48 kHz。
- 檔案上限 500 MB；每個語系最多 3 支。
- 封面預設是第 5 秒，可以改。

**內容規定：**
- App Review 2.3.4：「previews may only use **video screen captures of the app itself**」。可以加旁白，也可以加影片或文字覆蓋。
- App Previews 頁的規定：
  - 不能拍人或手指點螢幕，可以加觸控熱點圖形；
  - 建議用原生解析度、不要放大；
  - 轉場用溶接或淡入淡出；
  - 不寫價格，不寫時效字眼（例如季節或日期）；
  - 有內購才能用的功能，必須在片中或結尾卡揭露；
  - 字幕要讓靜音觀看也看得懂，並且停留夠久。
- **截圖做成的動畫算不算錄影：不算。** 2.3.4 寫的是螢幕錄影，用截圖平移、縮放做的片有被退件的風險。所以：
  - 雲端樣片只用來看節奏、字卡和結尾卡，畫面上有「DRAFT／草稿」字樣；
  - **正式上傳版必須用模擬器實錄**，錄影步驟已寫進 `.github/growth/LOCAL_TASKS.md`；
  - `render_preview.mjs --final` 會檢查每一段都有錄影，少一段就不出片。
- 裝置外框：官方文件沒有明文禁止，但要求畫面是 App 本身。樣片只用螢幕畫面加圓角，沒有手機外框，也沒有 3D 鏡頭。
- PPO 規定：
  - 一個 App 同時只能有一個測試，最多跑 90 天，開始後不能修改；
  - 可以只選部分語系，沒選到語系的使用者不進測試；
  - 新的預覽影片要經 App Review 核准。沒有換 icon 時，可以不跟新版本一起送；
  - 結果在 App Analytics 看，信心水準以 90% 為門檻。

## 3. 樣片內容（第二版，15.5 秒）

第一版（20 秒、每段 3–4.5 秒、慢推）Caitlyn 覺得太慢、沒特效、文案不夠讓人想下載，所以整個重做。

**節奏：** 120 BPM，一拍 0.5 秒。每 1.5–2.5 拍（0.75–1.25 秒）就切一次鏡頭，剪點落在拍子或半拍上；鏡頭本身也一直在推，沒有超過 1.2 秒不動的畫面。

| 時間 | 內容 |
|---|---|
| 0–1.75 秒 | 鉤子：大字痛點先佔滿畫面，0.6 秒內縮到上方，App 畫面重擊進場 |
| 1.75–13 秒 | 6 張利益字卡，每張 1.5–2.5 秒，每張配 1–2 個鏡頭推到 UI 上的那個元素 |
| 13–15.5 秒 | 結尾卡：圖示彈入、App 名稱、一句價值、產品頁上的一句佐證、三張實際畫面展開、內購揭露 |

**效果：** 彈簧推近；甩鏡（水平動態模糊）；圓形遮罩轉場；重擊進場；字卡逐字彈出，關鍵字有螢光底掃過；標示框自己畫出來、其餘畫面變暗；點擊漣漪（沒有手）；數字計數跳到 UI 上的同一個數字（Mochi 101、BattAI 52/100 和 78%、Cyca 8 天和 46）；光澤掃過；背景有視差光斑。

**音樂與音效：** 由 `scripts/preview_audio.py` 依同一份鏡頭表自動合成，我們自有：每拍大鼓、16 分音符鈸、反拍低音；第一格和結尾卡有重擊，甩鏡和轉場前有咻聲，點擊、計數各有音效，結尾前一拍是小鼓漸強。最後用 ffmpeg 正規化到 −16 LUFS。

**文案規則：** 痛點 → 解法 → 畫面證明 → 下載理由；每張 2–5 個字；每句都在產品頁上或畫面裡看得到；沒有「最好」、沒有競品、沒有價格。每款寫兩組，採用 A：

| App | 採用 A（en／zh-Hant） | 備選 B |
|---|---|---|
| Mochi | To-do lists feel like chores? → Make it cute → Tap. Done. → 101 cozy themes → Add emoji to tasks → Right on your Home Screen → So satisfying to tap／待辦清單 看了就累？→ 換成可愛的 → 點一下 完成 → 101 款療癒主題 → 任務配上表情符號 → 桌面一眼看到 → 點完成超有感 | Your list, but cute／清單也能這麼可愛 開場，收在 Get things done, gently／溫柔地把事情做完 |
| BattAI | Battery draining faster? → Get your health score → See what's dragging it down → Know when it hits 80% → Measured or estimated? Labeled. → Reports, never uploaded → No ads. No tracking.／電池越來越不耐用？→ 看你的電池健康分數 → 扣分原因 一次看懂 → 預估何時掉到 80% → 實測、推估 標清楚 → 報告不會上傳 → 無廣告 無追蹤 | When will it hit 80%?／哪天掉到 80%？ 開場，第二張 Score: 52/100. Why?／52 分？原因在這 |
| Cyca | Who sees your period data? → No one. No account. → Stays on your iPhone → Next period in 8 days → Fertile days at a glance → Your daily body forecast → Plan your best days／誰看得到你的經期資料？→ 沒有人。不用帳號 → 只留在你的 iPhone → 8 天後 下次經期 → 易孕期 一眼看清 → 每天的身體預報 → 排出你的好日子 | Your cycle, private.／經期紀錄 只給你看 開場，收在 Plan around how you feel／照感覺安排生活 |

- 為什麼選 A：A 都用問句開場，直接點出使用者的痛點，第二張馬上給答案；B 比較像功能介紹，適合之後當第二個 treatment。
- 結尾卡：
  - Mochi：Cute to-do lists, 101 themes／可愛待辦清單 101 款主題；佐證：Widgets · Apple Watch。
  - BattAI：Your battery health, explained／電池健康 一看就懂；佐證是副標：Clear rules, sources, and limits。
  - Cyca：Your cycle stays yours.／你的週期 只屬於你；佐證：No account · No cloud · No tracking。
- 內購揭露：
  - Mochi：部分主題與功能需 App 內購買（101 款中 96 款需進階版）；
  - BattAI：部分功能需 App 內購買（到 80% 的時間預估與報告）；
  - Cyca：預測與部分功能需 Cyca Pro，另外加註「非醫療器材」。
- 刪掉的說法：第一版 BattAI 的「送修、二手轉賣都用得上」在產品頁上找不到，第二版改成產品頁有寫的「報告在這台裝置產生、不會上傳」。
- **封面：第 1 秒**。這時鉤子字卡已經縮到上方、畫面到位。
- 語系：en、zh-Hant。zh-Hant 截圖的版面有一處不同（Cyca「On-device」那行比較高），已在鏡頭表加語系覆蓋。

產生方式（00_GrowthEngine `shorts/`）：
- `app_preview.json`：鏡頭表（畫面、拍數、轉場、鏡頭起訖、標示框、點擊、計數）、兩組文案、結尾卡、揭露；
- `src/preview/`：獨立的 Remotion 入口，不動鉤子片模板；
- `scripts/preview_audio.py`：依鏡頭表合成音樂與音效；
- `scripts/render_preview.mjs`：輸出到 `out-preview/<app>/`，`--copy B` 可出備選文案。

## 4. 測試設計

| 項目 | 設定 |
|---|---|
| 對照組 | 現行產品頁，不動 |
| Treatment（1 個） | 跟原頁完全相同的截圖，**只在第一格加上 App Preview**（iPhone 6.9 吋）。一次只改一個變數 |
| 語系 | Mochi：English (U.S.)＋Chinese (Traditional)；BattAI、Cyca 同上 |
| 流量比例 | **50%**：一個 treatment，所以是 50/50 |
| 最短天數 | 14 天，涵蓋兩個完整的週循環。在這之前即使顯示勝負也不動作 |
| 最長天數 | 90 天（Apple 上限） |
| 主要指標 | ASC 的轉換率（首次下載÷不重複曝光），以及 treatment 相對原頁的提升和信心水準 |
| 守門指標 | 每週看一次付費數和退款數，資料來自 portfolio-revenue。付費數降低 30% 以上，而且曝光沒有同步下降，就提前停止 |

**統計檢定力估算**（50/50 分流，90% 信心水準，80% 檢定力）：
- 曝光數取前五大國家裡英語和繁中市場的 30 天量。
- Mochi（約 3.1 萬次／月，轉換率 3.5%）：
  - 30 天可以偵測約 15% 的相對提升；
  - 60 天約 11%；
  - 90 天約 9%。
  - **只有 Mochi 有足夠的量看出中等幅度的差異。**
- Cyca（約 9,700 次／月，轉換率 1.4%）：90 天約 25%。效果要很大才看得出來。
- BattAI（en＋zh-Hant 約 2,000 次／月）：90 天約 37%。**樣本不足**。建議核准後把 ja、ko 一起加進 treatment（KR 和 JP 是 BattAI 的前兩大市場），每月曝光量大約會翻倍。

## 5. 停止與推出規則

1. **贏**：開跑滿 14 天後，ASC 顯示 treatment「performing better」，而且信心水準 ≥ 90%。
   - 按「Apply Treatment」套用到原頁；套用後測試會結束。
   - 然後把同一支影片推到其他語系：用同一個分鏡另外出片，錄影也要那個語系的。
2. **輸**：任何時候顯示「performing worse」，而且信心水準 ≥ 90%（14 天內也算），立刻 Stop Test，原頁不動。
3. **沒有結論**：90 天到了仍然沒有 90% 的結果，就不推出、原頁不動。記錄下來，改測別的鉤子（b 或 c）。
4. 守門指標觸發（見第 4 節）時，提前 Stop Test。
5. **只有贏的 treatment 才推出。** 測試期間不發新版本，避免版本裡的素材改動影響結果。真的要發，就先停止測試。

## 6. 執行步驟（Caitlyn 核准後由本機 session 做）

### 6.0 前置檢查（只用 GET）

```bash
cd ~/00_GrowthEngine/aso
python3 ppo.py list 6785004775   # Mochi
python3 ppo.py list 6802423998   # BattAI
python3 ppo.py list 6782251621   # Cyca
```

- **Mochi 有一個既有的「只重排截圖、30% 流量」PPO**，是 ASC 寫入授權例外 17 `MOCHI_PPO`，到期日 2026-11-15。
  - 如果那個測試已經建立或正在跑，因為同時只能有一個測試，Mochi 的影片測試要排在它結束之後；
  - 如果它還沒啟動，請 Caitlyn 二選一，不要兩個都建。
- 用 GET 確認三款原頁的 iPhone 6.9 吋目前**沒有** App Preview。如果已經有，treatment 就是「換成新影片」，計畫要改寫。
- 確認三款都是 Ready for Distribution。

### 6.1 正式版影片

照 `LOCAL_TASKS.md`「App Preview 實錄」錄 26 個畫面，然後在 `shorts/` 執行 `node scripts/render_preview.mjs mochi battai cyca --final`，再給 Caitlyn 看正式版。

### 6.2 ASC 網頁操作（每款各做一次）

步驟 1–4 和 7 取自 Apple 說明頁「Create a test」「Configure test treatments」「Run a test」。

1. Apps → 選 App → 左側欄 **Product Page Optimization** → **Create Test**。已經建過測試的話，按 Product Page Optimization 旁的 **+**。
2. 名稱：
   - Reference Name：`app-preview-slot1-2026-10`；
   - Number of Treatments：**1**；
   - Traffic Proportion：**50%**。
3. Localizations：只勾 **English (U.S.)** 和 **Chinese (Traditional)**（BattAI 依第 4 節可以加日文、韓文）。
4. 可以展開「Estimate Your Test Duration」，選 10% 看預估天數，只當參考。然後按 **Create Test**。
5. 把 Treatment A 改名為 `preview-slot1`：按 Edit Name → OK。
6. 切到 **App Previews and Screenshots** 分頁。
   - 每個語系在 **iPhone 6.9" Display** 的 App Previews 拖入對應的影片：en-US 用 `<app>_en_preview.mp4`，zh-Hant 用 `<app>_zh-Hant_preview.mp4`；
   - 封面用 `<app>_<locale>_poster.png` 對應的時間點 **00:00:01:00**（在影片上設定封面；Apple 說明頁沒寫這顆按鈕的名稱，以 ASC 當下介面為準）；
   - **截圖不動**。沒改的裝置尺寸會沿用原頁素材。
7. 按 **Save**，回到測試頁，右上角按 **Start Test**。
   - 系統提示要送審時按 **Add for Review**，選建立新的送審單，再按 **Submit for Review**；
   - 沒有換 icon，所以不用跟新版本一起送。
8. 核准後狀態會變成 Running，測試開始。結果要等關聯到 5 次首次下載後，才會出現在 App Analytics。
9. 每週在 Product Page Optimization 和 App Analytics → Product Page Optimization 檢查一次，依第 5 節判斷。

### 6.3 用 API 執行（選用）

- `aso/ppo.py` 可以 `create`（`--traffic 50`）、`treatment`、`start --start`、`stop`；
- 但 `social/upload_apppreview.py` 目前只會上傳到**版本**的語系，還不會上傳到 treatment 的語系；
- 要用 API 的話，`appPreviewSets` 的關聯要改成 `appStoreVersionExperimentTreatmentLocalization`，previewType 用 6.9 吋的類型，`previewFrameTimeCode` 設 `00:00:01:00`；
- 執行前要確認寫入授權。授權程式 `lib/asc_write_authorization.py` 不能改；
- **建議第一次直接用網頁操作**（6.2）。

## 7. 樣片與檔案

**審閱頁**（第二版 6 支樣片都嵌在頁面裡，附兩組文案和合規結論；同一個網址，第一版已被取代）：https://claude.ai/artifact/Fn7NTZRGuaByzg1DuWbHrT
- 預設是私人頁面，要從頁面的 Share 選單分享給 Caitlyn。

**原尺寸 886×1920 下載**（第二版，litterbox，上傳後 72 小時有效，約到 2026-10-17 晚上）：

| App | en | zh-Hant |
|---|---|---|
| Mochi | https://litter.catbox.moe/bqdye5.mp4 | https://litter.catbox.moe/ybj32m.mp4 |
| BattAI | https://litter.catbox.moe/se9av0.mp4 | https://litter.catbox.moe/rm4yrk.mp4 |
| Cyca | https://litter.catbox.moe/1vsezh.mp4 | https://litter.catbox.moe/3buzw8.mp4 |

- catbox 擋雲端 IP，所以這次改用 litterbox 的 72 小時連結。
- 走鉤子片的 Mac 上傳路線（clips-out）要 force-push，所以這次沒用。
- 原始檔在 00_GrowthEngine `shorts/out-preview/<app>/`，不進 git：
  - `_preview.mp4`：正式規格；
  - `_poster.png`：第 1 秒的封面；
  - `review/`：審閱用小檔。
- 需要的話，在 `shorts/` 執行 `node scripts/render_preview.mjs mochi battai cyca` 就能重出。
