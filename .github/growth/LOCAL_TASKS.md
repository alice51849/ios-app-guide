# 本機 Claude 待辦（雲端外宣 session 維護）

Caitlyn 在本機對話貼一行「請照這個檔執行」時，就照下面做。授權由她在那一行裡說明。授權範圍也寫在 `.github/growth/app-improvements.json` 的 `standing_approval`：

- 外宣直接做。
- 不改 App 本體。
- 副標與關鍵字只要經過一個以上模型驗證，就直接改 ASC。
- UsageNow 的標題也授權改。

## App Preview 實錄：Mochi、BattAI、Cyca（2026-10-14 新增）

> **這段只錄影、不碰 ASC。** 上傳和建立 PPO 測試要等 Caitlyn 看過樣片並核准，步驟在 `.github/growth/drafts/app-preview-ppo/plan.md`。

**為什麼要實錄：**
- App Review 2.3.4 寫明 App Preview「只能使用 App 本身的螢幕錄影」，可以加旁白與文字覆蓋。
- 雲端做的樣片是拿 App Store 截圖加平移與標示框，只能給 Caitlyn 看節奏和字卡，**不能上傳**。
- 樣片右上角有「DRAFT／草稿」字樣。

**模擬器與錄影設定（每款、每語言都一樣）：**
1. 機型用 6.9 吋（畫面 1320×2868）：`xcrun simctl list devices available | grep "Pro Max"`，選 iPhone 17 Pro Max（沒有就 16 Pro Max）。
2. 開機並統一狀態列：
   ```bash
   xcrun simctl boot "iPhone 17 Pro Max"; open -a Simulator
   xcrun simctl ui booted appearance light
   xcrun simctl status_bar booted override --time "9:41" --dataNetwork wifi --wifiMode active --wifiBars 3 --cellularMode active --cellularBars 4 --batteryState charged --batteryLevel 100
   ```
3. 安裝現行上架版的程式碼：
   - 資料夾用 `python3 -c "import sys; sys.path.insert(0,'$HOME/00_GrowthEngine/lib'); from app_dirs import app_dir; print(app_dir('Mochi'))"` 找，BattAI、Cyca 同理；
   - Bundle ID 用 `xcodebuild -showBuildSettings | grep PRODUCT_BUNDLE_IDENTIFIER` 查；
   - 只 build 到模擬器，不改程式、不送審：`xcodebuild -scheme <Scheme> -destination 'platform=iOS Simulator,name=iPhone 17 Pro Max' -derivedDataPath /tmp/pv-dd build`，然後 `xcrun simctl install booted /tmp/pv-dd/Build/Products/Debug-iphonesimulator/<App>.app`。
4. 語言：每次啟動時指定，不動系統設定。
   - 英文：`xcrun simctl launch --terminate-running-process booted <bundle-id> -AppleLanguages "(en)" -AppleLocale en_US`
   - 繁中：`xcrun simctl launch --terminate-running-process booted <bundle-id> -AppleLanguages "(zh-Hant)" -AppleLocale zh_TW`
5. 示範資料：
   - 跟商店截圖用同一套示範資料。產生 `*_home_unlocked.png` 那套截圖流程的啟動參數或 StoreKit 測試設定都可以用；
   - 不要用任何真人的資料（Cyca 的經期、BattAI 的電池紀錄都一樣）；
   - 需要內購才看得到的畫面，用 Xcode 的 StoreKit Configuration 在模擬器解鎖。樣片結尾卡已經寫了內購揭露。
6. 第二版是「一個畫面錄一個檔」，不是一段一檔。先擺好畫面再開始錄，按 Ctrl-C 停：
   ```bash
   mkdir -p ~/Desktop/preview_raw
   xcrun simctl io booted recordVideo --codec=h264 --force ~/Desktop/preview_raw/<app>_<locale>_<畫面>.mov
   ```
   - 每個畫面錄 **8 秒**。成片裡同一個畫面會被切成 2–3 個鏡頭，管線會從錄影裡接著往下取，不會重複同一秒。
   - 鏡頭推近、標示框、點擊漣漪、計數都由管線加，錄影時只要在對的時間點做對的動作，畫面不要自己捲太快。
   - 不要出現手指、鍵盤或滑鼠游標，也不要出現模擬器外框。`recordVideo` 本來就只錄畫面。

**要錄的畫面（每款 en 和 zh-Hant 各錄一套；Mochi 4 個、BattAI 4 個、Cyca 5 個，共 26 個檔）：**

| App | 畫面檔名 | 用在哪幾張字卡（採用文案 A） | 錄什麼 |
|---|---|---|---|
| Mochi | s02 | 鉤子、「點一下 完成」、「點完成超有感」 | Today 清單（跟截圖 s02 一樣的示範任務）；第 2 秒點「Water the plants」的圓圈，第 5 秒點「Morning stretch」 |
| Mochi | s03 | 「換成可愛的」、「101 款療癒主題」 | 點調色盤進 Skins，第 1 秒點「Mochi」主題，之後慢慢捲過 Pink 區 |
| Mochi | s04 | 「任務配上表情符號」 | 編輯任務畫面的 Emoji 區，第 2 秒點星星 |
| Mochi | s01 | 「桌面一眼看到」 | 主畫面上的 Today 小工具（先加好），靜止 8 秒 |
| BattAI | 01 | 鉤子、「實測、推估 標清楚」 | Today 分頁，電量卡上的 78% 與「Measured」標籤 |
| BattAI | 02 | 「看你的電池健康分數」、「扣分原因 一次看懂」 | Health：先停在 52/100 分數卡 3 秒，再慢慢捲到「What shapes the score」 |
| BattAI | 04 | 「預估何時掉到 80%」 | Trends 分頁，「Monthly capacity change」和鎖住的「Estimated time to 80%」 |
| BattAI | 05 | 「報告不會上傳」、「無廣告 無追蹤」 | More 分頁，第 2 秒點「Reports」，返回後停在 Privacy |
| Cyca | s01 | 鉤子、「8 天後 下次經期」 | Today（Next period 8 days、Predictions），靜止或微捲 |
| Cyca | s03 | 「易孕期 一眼看清」 | Calendar 分頁，第 3 秒點 25 號 |
| Cyca | s05 | 「沒有人。不用帳號」、「只留在你的 iPhone」 | 打開「Care for you」，捲到底部「Estimated from your cycle · On-device」 |
| Cyca | s02 | 「每天的身體預報」 | 打開 Body Forecast，停在分數 46，再微捲到各項指標 |
| Cyca | s06 | 「排出你的好日子」 | 打開 Smart Planner，停在「Best days for big plans」，再捲到 The weeks ahead |

- 點擊時間以 `shorts/app_preview.json` 每個鏡頭的 `tap` 為準（那是鏡頭內的秒數）；錄影對不上也沒關係，對不上時把那個鏡頭的 `tap` 刪掉就好。
- BattAI 的模擬器沒有電池，所以用 build 內建的示範資料集（跟截圖一樣是 1,448 筆、31 天）。如果用測試 iPhone 錄，就用 iPhone 的螢幕錄影功能，錄好轉成 1320×2868。
- Mochi s01 錄的是主畫面上的小工具。小工具屬於 App 的一部分，但如果審核有意見，就把那兩個鏡頭換成 s02。

**轉檔、放進管線、出正式版（在 00_GrowthEngine/shorts）：**
```bash
for f in ~/Desktop/preview_raw/*.mov; do
  b=$(basename "$f" .mov); app=${b%%_*}; rest=${b#*_}; loc=${rest%_*}; scr=${b##*_}
  mkdir -p public/recordings/$app/$loc
  ffmpeg -y -i "$f" -vf "scale=1320:2868,fps=30" -c:v libx264 -crf 16 -pix_fmt yuv420p -an public/recordings/$app/$loc/$scr.mp4
done
node scripts/render_preview.mjs mochi battai cyca --final   # 每個畫面都有錄影才會出片，沒有 DRAFT 字樣
```
- 輸出在 `out-preview/<app>/<app>_<locale>_preview.mp4`，規格是 886×1920、30 fps、H.264 High@4.0、約 11 Mbps、AAC 256k 立體聲 48 kHz、15.5 秒。
- 檢查 `out-preview/<app>/<app>_<locale>_poster.png`。這是第 1 秒的畫面，也就是建議的封面。
- 鏡頭焦點、標示框、計數的座標會自動換算成完整螢幕的位置，但還是要用眼睛看一遍（`--still` 會輸出幾張檢查用的畫格）。對不準就在 `app_preview.json` 那個鏡頭加語系覆蓋，例如 `"zh-Hant": {"ring": [...]}`。
- 正式版給 Caitlyn 看過才上傳。

## 新 App：針孔偵測（58_Lensafe，2026-10-14 新增）

**狀態（10-15）：** 雲端已寫完原始碼，在 00_GrowthEngine 的 `lensafe` 分支，最新 commit 是 faaad46，路徑 `newapps/58_Lensafe/`。目前還沒有用 Xcode 編譯過。

**本機第一步：** 匯入成獨立 repo 並驗證。

```
cd ~/00_GrowthEngine && git fetch origin lensafe && git worktree add /tmp/lensafe-src origin/lensafe
cp -R /tmp/lensafe-src/newapps/58_Lensafe ~/58_Lensafe && git worktree remove /tmp/lensafe-src
cd ~/58_Lensafe && git init -q && git add -A && git commit -qm "Lensafe 初始匯入（00_GrowthEngine lensafe faaad46）"
gh repo create alice51849/58_Lensafe --private --source=. --push
brew install xcodegen; xcodegen generate
(cd Packages/LensafeCore && swift test) && Scripts/check_strings.sh && Scripts/scan_release_for_demo.sh
```

接著：
1. 在 iOS 26 模擬器和真機上建置，修到零錯誤。
2. 照 `Docs/README.md` 的「裝置風險」逐項實測：Lock Screen 擴充裡的手電筒、多鏡頭加手電筒脈衝、Camera Control 滑桿、Release 建置不含 demo、各地緊急電話號碼等。
3. 照規格 §16 的 1～7 步跑新 App 管線：ledger、spam／requirements 閘門、newapp_register、商標查詢後再建 Bundle ID 和 ASC、US$4.99 價格收據、截圖（先照 `Docs/BUILD.md` §5～6 錄 `demo.mov`）、release 閘門加獨立審查、`submit_one.py`。審查備註貼 `Docs/REVIEW_NOTES.md` 的 Part A。


> 規格：`.github/growth/drafts/new-app-hidden-camera/spec.md`（先 `git pull`）。店主已經決定好的事項：
> - 名稱 **Lensafe**；
> - **付費下載 US$4.99**：沒有內購、沒有免費版、沒有訂閱，也不做早鳥價；
> - **打開就是相機**，自動標出可能的鏡頭；
> - iOS 26 起、Liquid Glass。
>
> 這個任務**不受「暫不改 ASC」的限制**：那條說的是不改既有 App 的文字，建立新 App 的紀錄是店主這次明確要求的新任務。

**給店主：**
1. 在本機 Claude 對話貼下面整段提示。ASC 的 App 紀錄、Bundle ID、價格都由本機新 App 管線自動建立，**不用自己到 App Store Connect 手動建**。
2. 只有兩種情況要你出手：
   - 本機回報「Paid Apps Agreement 不是 Active」：到 App Store Connect →「商務（Business）」→「協議（Agreements）」，把付費 App 協議的銀行和稅務資料補齊；
   - 本機回報商標檢索有衝突：從十選一的其他候選名重新挑一個。
3. 準備兩樣實測和拍片用的東西：
   - 一台便宜的測試用針孔或小型 Wi-Fi 攝影機（網購即可）；
   - 一支電視遙控器。

   QA、App Preview 和鉤子片都要用真機實拍，模擬器沒有相機。

**貼給本機 Claude 的提示（整段複製）：**

```
請照工作室的標準新 App 流程，依 ios-app-guide 的 .github/growth/drafts/new-app-hidden-camera/spec.md（先 git pull）建立並送審第 58 款 App「Lensafe」。資料夾與收據鍵用 58_Lensafe，Bundle ID 用 com.alice51849.Lensafe，內部識別名用 Lensafe。顯示名稱只從一個改名點讀取：Packages/LensafeFeatures/Tools/brand.json，加上 LENSAFE_DISPLAY_NAME，加上 L10n key app.name。

店主已核准（2026-10-14）：
- 名稱 Lensafe；
- 付費下載 US$4.99，無內購、無免費版、無訂閱、不做早鳥價；
- iOS 26 起；
- 打開就是全螢幕相機，自動標記（spec 的 ★ 節優先於其他章節）。

步驟：
1. 台帳：~/00_Standards 的 app-portfolio.md 新增第 58 列；app-requirements.md 新增「### 58. Lensafe — 58_Lensafe」段落，內容取自 spec。
2. 寫 StoreAssets/contracts/portfolio-distinctness.json（phase=concept）：以 spec 9A.5 為底稿，portfolioComparisons 補齊 01–57。
3. 依序跑 portfolio_spam_gate.py --phase concept、requirements_gate.py、newapp_register.py 58_Lensafe，再寫 new_app_gate.py receipt 58_Lensafe requirements。
4. 正式商標檢索：USPTO、EUIPO、JPO、KIPO、TIPO，類別 9 與 42。有衝突就停下來回報，不要建 Bundle ID。
5. 商標沒問題後，建立 Bundle ID 和 ASC App：
   - 名稱 Lensafe、主要語言 English (U.S.)、主類別 Utilities、次類別 Travel、SKU 照工作室慣例；
   - Pricing and Availability → Price Schedule → Base Country United States → $4.99；
   - 確認 KR ₩7,700／JP ¥800／TW NT$150，其他國家用 Apple 自動等值價；
   - 先確認 Paid Apps Agreement 是 Active，不是就停下來回報店主；
   - App Privacy 填 Data Not Collected；
   - 年齡分級照實填問卷。
6. 用 XcodeGen 建工程，結構和設計慣例對齊 57_OFFDAY：
   - 參考 project.yml、DESIGN_V2/V4、15_pricing_study；
   - 只參考，不複製程式或字串；
   - 照 spec 第 4、5、6、12 節實作：H1 零點擊偵測、H2 確認這一點、H3 覆蓋率、IR 與 multicam 子母畫面、Wi-Fi／藍牙、清單、PDF 報告；
   - H5 LiDAR 是實驗功能，預設關閉；
   - 手電筒脈衝 ≤ 3 Hz；
   - 不做磁力計偵測，不做假雷達、假進度。
7. 約 50 種語言、App 內切換語言：en、ko、ja、zh-Hant 的中繼資料與商店文案直接用 spec 第 10、11 節（字數和去重已驗證）；其他語言由你用母語語氣生成，並各自去重。
8. 在真機用自備的測試鏡頭跑 spec 第 6.1 節的 QA 矩陣和第 15 節的驗收清單，結果寫進 Docs/QA。
9. 截圖 7 張加 App Preview，照 spec 第 7.3A、11、12.6 節，全部用真機實拍；偵測畫面不可以合成。
10. 照管線補齊其他收據。price_policy_ok 要註明店主核准付費下載、無內購；iap_binary_ok 標成不適用（照 gate 的規定）。
11. 跑 portfolio_spam_gate.py --phase release（原始碼相似度每一款都要 ≤ 0.35），再找獨立的 Max 審查。審核備註貼 spec 9A.4，然後 submit_one.py 送審。
12. 回報：商標檢索結果、ASC App ID、各 gate 與收據狀態、QA 數字、送審狀態。上架後把 App Store ID 寫回 spec，雲端才能接上鉤子片、Telegram、Threads、GEO 頁（spec 第 13、14 節）。
```

## 社群授權：Pinterest、TikTok（2026-10-14 新增）

Caitlyn 會在本機對話貼「請照 LOCAL_TASKS 的社群授權段執行」，後面附上 App ID、secret 或 Client Key、Secret。這些值只存在這台 Mac，不要 commit，也不要貼到任何地方。

**Pinterest**
1. `mkdir -p ~/.pinterest && chmod 700 ~/.pinterest`
2. 寫入 `~/.pinterest/client_secret.json`：`{"app_id":"<她給的>","app_secret":"<她給的>","redirect_uri":"http://localhost:8085/"}`，然後 `chmod 600`。
3. `cd ~/00_GrowthEngine/social && venv/bin/python pinterest_upload.py --auth-only`。這會開瀏覽器，請她按「允許／Give access」。看到「✅ 授權成功」才算完成。
4. 驗證：`venv/bin/python creds_probe.py`（或 social-creds-probe.yml）。reports/social-creds-status.json 的 pinterest.valid 要是 true。
5. 回報雲端：pinterest valid=true 和看板名稱。雲端會把每日發文接上（Caitlyn 10-14 同意開通）。

**TikTok**
1. `mkdir -p ~/.tiktok && chmod 700 ~/.tiktok`
2. 寫入 `~/.tiktok/credentials.json`：`{"client_key":"<她給的>","client_secret":"<她給的>","redirect_uri":"http://localhost:8090/"}`，然後 `chmod 600`。
3. `venv/bin/python tiktok_oauth.py auth-url`，用 `open "<印出的網址>"` 開瀏覽器，請她按「Authorize」。
4. 瀏覽器會跳到 localhost:8090 並顯示連不上，這是正常的。請她把網址列整串複製給你，再跑 `venv/bin/python tiktok_oauth.py token "<整串網址>"`。
5. 跑 creds_probe 驗證 tiktok.valid=true，並回報雲端。審核通過前只能發成「僅自己可見」，所以先不排程；等 Content Posting API 審核通過再開。

## 背景

- Guide repo：`~/00_GrowthEngine/geo/pages`（= GitHub alice51849/ios-app-guide）。GrowthEngine：`~/00_GrowthEngine`。
- `_engine/` 是 GrowthEngine 的逐位元組鏡像。GEO 改動要先改 00_GrowthEngine，再鏡像到 Guide。
- 待辦清單是 `.github/growth/app-improvements.json`。office.cait518.cc 的外宣頁直接讀 main 上的這個檔，所以狀態要隨時更新。

> **2026-10-14 更新：Caitlyn 決定暫不改 ASC。** 下面所有套用 ASC 的步驟（UsageNow 與其他 App 的 asc-payload）都先跳過，除非她在本機對話裡再次明確要求。UsageNow 1.0.2 草稿已填的新文字，只有在她說「照備份改回去」時才改回。

> **2026-10-14 新增：7 秒鉤子片（高品質短影音）。** 程式和分鏡在私人 repo `~/00_GrowthEngine/shorts/`（先 `git pull`），說明見該資料夾的 README.md。
> 1. 準備素材：
>    ```
>    cd ~/00_GrowthEngine/shorts
>    npm install
>    python3 scripts/prepare_shots.py --all
>    python3 scripts/make_audio.py
>    ```
> 2. 在地化截圖：`storyboards/` 裡每款 App，如果 `~/00_GrowthEngine/aso/shots_out/<目錄>/APP_IPHONE_67/` 存在（目錄對照見 `social/breakout/localized_variants.json` 的 shots_dir），就跑 `python3 scripts/prepare_shots.py <app> --localized <那個路徑>`。跑完用 `python3 scripts/grid.py` 或直接看圖，確認各語言的 `NN.png` 跟基準組是同一個畫面。不是的話，把那個語言的資料夾刪掉，改用英文畫面。
> 3. 渲染：`node scripts/render.mjs --all`，產出在 `out/<app>/<app>_<語言>.mp4`（有音樂）與 `_silent.mp4`（無聲）。每款抽一支從頭看到尾，確認字沒有被切、點擊位置正確。
> 4. 上架：用既有的 YouTube 上傳程式（`social/yt_upload.py` 與 48 語標題流程），每天最多 3 支，先上 Mochi、Unblurry、LockHour、Lumi Mission、ScanTo、PhotoCream。
>    - 標題用 `videogen/search_demand.py` 的已驗證查詢句開頭。
>    - 9/14 起暫停上傳的前後比較今天（10/14）到期：先把比較結果寫進回報，再開始上傳新片。
>    - 無聲版放在 `out/` 給 TikTok／IG 手動配熱門音樂用。
>    - **Android 也上線了：** App 在 `_engine/geo/data/android_live_snapshot.json` 裡（已上 Google Play）的，YouTube 說明欄除了 App Store 連結也放該檔的 `play_url`（加 `&referrer=utm_source%3Dlumi_social%26utm_campaign%3Dh7_<app>_<語言>_yt`）。
> 5. **補素材給雲端：** 下面這些 App 在 `social/assets/` 沒有截圖，雲端做不了它們的鉤子片。請把每款 App Store 上的 iPhone 6.9 吋截圖（1320×2868 或 1290×2796）照 `01.png`、`02.png`… 的格式放進 `social/assets/<key>/`，commit 並 push，雲端就會接著寫分鏡：claudeusagemini（最優先）、countdaysnow、studydown、stayclock、savetag、shotinbox、picclear、qrcodehalo、battai、dbhalo、zipbox、sononote、cvdesk、ledmovingtext、lumibopomofo、lumibopomofopro、lumiletterspro、lumimathpro、lumimissionpro、snapport、moneytag。

> **2026-10-14 最優先：打開 In-App Events 送審（Caitlyn 明確指示「打開 In-App Events 送審」）。** 雲端已寫好修改，但雲端無法執行閘門測試。
> 1. `cd ~/00_GrowthEngine && git pull`
> 2. 套用修改：`git apply lib/proposals/2026-10-14-iae-seasonal-submission.patch`。內容：只允許名稱以 `S26-` 開頭的季節活動送審；送出前逐筆回讀 ASC，送審單裡只要有一筆不是季節活動就拒絕，所以舊的每日型草稿和 Cyca 的殘留項目永遠送不出去；MARKETING 期限延到 2027-04-30。
> 3. 跑 `python3 -m pytest -q lib/test_asc_write_authorization.py`；要補測試就補。
> 4. 全綠才 commit 並 push。
> 5. 在 `aso/iae_seasonal.py` 加 `--submit` 模式（目前它刻意沒有送審程式，`write()` 也擋 reviewSubmission 路徑）：只送 `reports/iae-status.json` 裡 `readyToSubmit: true` 的 `S26-` 活動；該 App 已有未完成的送審單（READY_FOR_REVIEW／WAITING_FOR_REVIEW／IN_REVIEW／UNRESOLVED_ISSUES）就跳過並記錄；流程照 `aso/inapp_events.py` 的 `submit_event()`：建送審單 → 加這一個 appEvent → 回讀 items 確認只有這一筆 → `submitted: true`，失敗就把空送審單取消。補測試，並把 `iae-cycle.yml` 的 drafts 模式改成草稿建完接著 `--submit`，以後每週一全自動。
> 6. 立刻送這 5 個（event id）：S26-CDN-Suneung-D30 `6822784812`（CountDaysNow 6807079789，**10/16 前一定要送**）、S26-Bopomofo-Grade1-Nov `6822784905`（6773017109）、S26-Snapport-Holiday-Travel `6822785073`（6792856304）、S26-StayClock-Holiday-Desk `6822785247`（6814035888）、S26-Mochi-Fresh-Start `6822785328`（6785004775）。不要送任何名稱含 SKIPPED／ZOMBIE／do-not-submit 的舊草稿，也不要碰 Cyca 那張舊送審單。
> 7. 回報每個活動的送審狀態，並跑一次 `iae-cycle.yml`（status）更新報告。

> **2026-10-14 最優先：送 Apple 精選提名（Caitlyn 明確要求現在送）。** 這是提名，不是改 App，也不是改商店文字，不受「暫不改 ASC」限制。
> 1. 內容在 `.github/growth/drafts/apple-featuring-nominations.json`，共 6 款：CountDaysNow、LED Moving Text、Stay Clock、Snapport Lite、Mochi、Mochi DoneStamp。文字已對過商品頁，不要改寫內容。
> 2. 用本機的 ASC API 金鑰，每款建一筆 nomination：`POST /v1/nominations`。
>    - attributes：`name`、`type`、`description`、`publishStartDate`、`publishEndDate`、`deviceFamilies`、`supplementalMaterialsUris`（= supplemental_urls）、`hasInAppEvents: false`、`launchInSelectMarketsFirst: false`、`submitted: true`。
>    - relationships：`relatedApps`（= app_store_id）、`supportedTerritories`（= territories）。
> 3. API 不支援或回錯誤：改用 App Store Connect 網頁（Apps → 該 App → 「精選／Featuring」→「提名」→「+」），照檔案逐欄貼上。
> 4. 回報每款的 nomination id 與狀態。

> **2026-10-14 新增：LED Moving Text 鉤子片重拍（Caitlyn 嫌太醜）。** 商店截圖都是單色字，影片做不出繽紛感，所以改用模擬器實拍。
> 1. 在模擬器開 LED Moving Text（解鎖完整功能），做 5–6 個彩色看板：
>    - 彩虹字、漸層字。
>    - 不同顏色的 LED 邊框。
>    - 發光、點陣、脈衝等效果。
>    - 多款情境範本，用不同顏色（演唱會、接機、生日、店家告示）。
> 2. 編輯畫面和全螢幕播放畫面都要有。
> 3. 中文、英文各一組。
> 4. 截成 iPhone 6.9 吋直式圖，存成 `~/00_GrowthEngine/social/assets/ledmovingtext/s01.png`、`s02.png`…；中文版放 `zh-Hant/` 子資料夾。
> 5. commit 並 push，雲端就會重寫分鏡、重新渲染。
> 6. 這些是買斷解鎖後的功能，影片會加註「一次買斷解鎖」，不寫免費。

> **2026-10-14 新增：補齊截圖（Caitlyn 明確要求）。** HoursTag Lite（iPhone 1 張、iPad 1 張）、SaveTag（各 2 張）、Unblurry（各 2 張）在 App Store 上的截圖少於 3 張，美國、台灣、日本都一樣。
> 1. 每款做 5–6 張 iPhone 6.9 吋、5–6 張 iPad 13 吋截圖。用既有的 ASO 截圖流程（`~/00_GrowthEngine/aso/`）從模擬器實際畫面產生，字卡只寫商品頁上有的功能。
>    - Unblurry 可以直接用 `social/assets/unblurry/01–04.png` 的 4 張，再補 1–2 張。
>    - 50 個語系都要有，沒有在地化截圖的語系用英文版。
> 2. 截圖只能掛在可編輯的新版本上：
>    - 建立新版本號，只改版本號，不改程式。
>    - 建置並上傳，掛上截圖。
>    - 「新功能」寫「更新 App Store 截圖」（各語系翻譯）。
>    - 送審。
> 3. 回報每款的新版本號、截圖張數、送審狀態。

> **2026-10-14 最優先：Threads 全自動恢復。** Caitlyn 選擇重新開啟 threads-autopilot。
> 1. 在 ~/threads-autopilot（或本機對應路徑）用 `gh workflow enable multi.yml` 與 `gh workflow enable post.yml`（repo alice51849/threads-autopilot）；若已啟用就跳過。確認 self-hosted macOS runner 在線。
> 2. 做 claudeusagemini-16：UsageNow 加入 reviewed onboarding（照 reviewed_sources/countdaysnow.json 等前例），跑該 repo 測試、推送，讓 Threads 自動發 UsageNow。

> **UsageNow 1.0.2 草稿：照備份改回原文字。** Apple 不能刪除非第一版的待送審版本（DELETE appStoreVersions 會回 409），所以用 `.github/growth/aso/claudeusagemini-asc-backup-*.json` 把 1.0.2 的 name／subtitle／keywords 改回送出前的原值，讓草稿等於沒改過。這是 Caitlyn 2026-10-14 明確要求的還原，不算新的 ASC 改動。

> **2026-10-14 第一優先：匯出每款 App 的真實漏斗（給成長計畫用）。** 從本機最新的 ASC 資料（`~/.growth-private/asc-acquisition-feedback.json`、`portfolio-revenue/latest.*`、Sales and Trends，或重新拉 ASC Analytics，哪個最新用哪個）匯出到**私人** repo `00_GrowthEngine` 的 `reports/funnel-latest.json`，不可放進公開的 ios-app-guide。每款 App 要有：
> - app_key、app_store_id、價格模式與主要價格、guard 分類（健康／量太小／零成交／零流量／資料不足）
> - 最近 30 天的 impressions、product_page_views、first_time_downloads、paying_users 或購買筆數、proceeds_usd、refunds
> - 前 5 名國家的下載與收益、as_of 日期、來源檔名
>
> 另外附 portfolio 總計與 `~/.growth-private/asa-status.json` 的摘要（各 campaign 花費、安裝、CPI）。只匯出，不改設定、不開廣告。commit 並 push 00_GrowthEngine。

## 依序執行

1. `cd ~/00_GrowthEngine/geo/pages && git pull origin main`

2. **最高優先：claudeusagemini-14，把 UsageNow 商店文字套用到 ASC。**
   - 要套用的值在 `.github/growth/aso/claudeusagemini-asc-payload.json`。它的 `verification.apply_ready` 是 true：Opus 調教，加四個角度的驗證，再由 Fable 獨立複核通過。
   - 先從 ASC 讀出目前每個語系的 name、subtitle、keywords，備份成 `.github/growth/aso/claudeusagemini-asc-backup-<日期>.json`，並 commit。
   - 韓文線上值很可能和 `ko.expected_current` 不同。以線上實值為準，並在回報裡列出差異。
   - 只改 name、subtitle、keywords，其他欄位都不動。
   - Live 版本的這幾個欄位，要有可編輯的新版本才能改：
     - 已經有可編輯的版本：直接套用。
     - 沒有：建立新版本記錄、填好文字，然後停下來回報。不要自己建置、上傳 build 或送審，這些由 Caitlyn 決定。
   - 如果審查退件標題（2.3.7、4.1(c)、5.2.1），照 payload 的 `fallback_if_rejected` 處理。

3. **其他 App 的 `.github/growth/aso/<key>-asc-payload.json`：** 只改 subtitle 和 keywords。`verification.apply_ready` 是 true 的，照第 2 步的做法套用：先備份，只改這兩欄。

4. **ops-edge-beacon（高）：修 Cloudflare 分析標籤造成的驗證失敗。**
   - Cloudflare 把 open.cait518.cc 頁尾自動插入的分析標籤換成新版：src 是 `beacon.min.js/v4bc70e2c01a94c73b74392e4234840661791215815920`，integrity 是 `sha512-L0ha0OXavK/8okipN9F8BtP84dg9DUhPERbBXzwI6dgTA55d2+yweo3pn5CSFYs45/r8md2+xvUPtTdvTNRfjA==`，token 沒變。
   - 00_GrowthEngine `geo/deployment_generation.py` 的 `EDGE_BEACON` 還是舊版，所以 pages.yml 的 verify-live 每一頁都判定 digest drift。
   - 改成接受同一個 token 的 static.cloudflareinsights.com beacon，或直接更新成新值。跑測試，再鏡像到 Guide。
   - 驗證：`python3 _engine/geo/deployment_generation.py verify-live --deployment <線上 deployment.json> --site https://alice51849.github.io/ios-app-guide --site https://open.cait518.cc/ios-app-guide --receipt /tmp/r.json --attempts 2` 要通過。
   - 不需要重新發布。

5. **其他 owner 是 "local"、status 是 "todo" 的項目**，依 impact 由高到低做。先做這幾項：
   - qrcodehalo-01、wifiaidlite-02：公開頁面上的錯誤宣稱。
   - claudeusagemini-09：UsageNow 衝榜期間（到 10/27），Threads 每天發 1 則。用 `.github/growth/drafts/claudeusagemini/push-kit.json` 的台灣 Threads 貼文，跳過她已經手動發過的那則。
   - shotinbox-04、lumiweather-05、aim990-05、tripplanet-04、wordmatelite-03。
   - lumimission-03、lumibopomofo-08、lumibopomofopro-06、tripplanet-01、lumiweather-03b、aim990-04b。

   發文和文案的規則：
   - 每個帳號每天最多 3 則，連結放在留言。
   - 文案只寫商品頁上有的功能，不寫競品名，不用「最好／best」。

6. **每完成一項：**
   - 把 status 改成 "done"，加上 done_at（UTC）。
   - 跑 `python3 .github/scripts/test_app_improvements.py`。
   - commit，`git pull --rebase`，`git push origin main`。

7. **不用改 pages.yml，也不用重新發布。** 正式站 10/13 已經上線 29c5c8dd。

8. **不要設每日自動執行。** Caitlyn 要求剩下的工作改成 0 token 自動化，所以本機 Claude 只在她貼這一行時跑一次。也不要建立 launchd 或用 `--dangerously-skip-permissions` 的無人值守腳本。

9. **回報：** 每做完一段，用中文說明做了哪些項目、各推了哪個 commit。最後一行列出需要 Caitlyn 按允許的動作，沒有就寫「無」。
