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
- 長度 15–30 秒。我們做 **20 秒**。
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

## 3. 樣片內容（20 秒）

| 時間 | 內容 | 來源 |
|---|---|---|
| 0–3 秒 | 鉤子 | 分鏡第 1 段，即鉤子 a。沒有成效資料，所以用鉤子片目前的主鉤子 |
| 3–7.5 秒 | 功能 1 | 分鏡第 2 段 |
| 7.5–12 秒 | 功能 2 | 分鏡第 3 段 |
| 12–16.5 秒 | 功能 3 | 分鏡第 4 段 |
| 16.5–20 秒 | 結尾卡 | App 名稱（商店現行名稱）＋一句商店頁上的說法＋內購揭露 |

- 字幕上方 330px 固定字卡，60–84px 粗體，靜音也看得清楚。
- 結尾卡沒有「立即下載」、沒有價格、沒有「免費」。
- 結尾卡的句子：
  - Mochi：Plan your day with cozy calm／把每天整理得更療癒（副標）；
  - BattAI：Understand your battery over time／看懂電池隨時間的變化（宣傳文字）；
  - Cyca：The warm, private way to understand your cycle／溫柔又私密的週期夥伴（描述首句）。
- 內購揭露：
  - Mochi：96 款主題需進階版；
  - BattAI：到 80% 時間預估與報告在解鎖內容裡；
  - Cyca：預測需 Cyca Pro，另外加註「非醫療器材」。
- **封面：第 1 秒**。這時鉤子字卡已經完整顯示，主畫面也到位。三款的鉤子都是一句痛點問句或利益句，比功能畫面更能代表 App。
- 音樂：鉤子片管線自己合成的 120 BPM 音樂床，我們有權利使用，結尾 1.2 秒淡出。
- 語系：en、zh-Hant。分鏡還有 ja、ko、pt-BR 等，核准後一行指令就能補出。

產生方式（00_GrowthEngine `shorts/`）：
- `app_preview.json`：結尾句、揭露、時長、封面秒數；
- `src/preview/`：獨立的 Remotion 入口，不動鉤子片模板；
- `scripts/render_preview.mjs`：輸出到 `out-preview/<app>/`。

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

照 `LOCAL_TASKS.md`「App Preview 實錄」錄 24 段，然後在 `shorts/` 執行 `node scripts/render_preview.mjs mochi battai cyca --final`，再給 Caitlyn 看正式版。

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

**審閱頁**（6 支樣片都嵌在頁面裡，附合規結論）：https://claude.ai/artifact/Fn7NTZRGuaByzg1DuWbHrT
- 預設是私人頁面，要從頁面的 Share 選單分享給 Caitlyn。

**原尺寸 886×1920 下載**（litterbox，2026-10-17 前有效）：

| App | en | zh-Hant |
|---|---|---|
| Mochi | https://litter.catbox.moe/tpbv9n.mp4 | https://litter.catbox.moe/aulzjq.mp4 |
| BattAI | https://litter.catbox.moe/sc54o6.mp4 | https://litter.catbox.moe/mpnw0t.mp4 |
| Cyca | https://litter.catbox.moe/ogjp1k.mp4 | https://litter.catbox.moe/ygwbff.mp4 |

- catbox 擋雲端 IP，所以這次改用 litterbox 的 72 小時連結。
- 走鉤子片的 Mac 上傳路線（clips-out）要 force-push，所以這次沒用。
- 原始檔在 00_GrowthEngine `shorts/out-preview/<app>/`，不進 git：
  - `_preview.mp4`：正式規格；
  - `_poster.png`：第 1 秒的封面；
  - `review/`：審閱用小檔。
- 需要的話，在 `shorts/` 執行 `node scripts/render_preview.mjs mochi battai cyca` 就能重出。
