# 本機 Claude 待辦（雲端外宣 session 維護）

Caitlyn 在本機對話貼一行「請照這個檔執行」時，就照下面做。授權由她在那一行裡說明。授權範圍也寫在 `.github/growth/app-improvements.json` 的 `standing_approval`：

- 外宣直接做。
- 不改 App 本體。
- 副標與關鍵字只要經過一個以上模型驗證，就直接改 ASC。
- UsageNow 的標題也授權改。

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
