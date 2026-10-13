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
