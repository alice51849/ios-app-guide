# 英雄任務成果工具

第一波是 **多筆購物價格 → 工作時間比較表 → CSV**，不是工時打卡或薪資工具。
HoursTag 與 HoursTag Lite 共用同一任務 canonical。依據是既有產品契約、
`hourstag_work_hours_tool.py` 及 publisher intent catalog；**不是已測得的搜尋量**。
未配置 adapter 的 App 留在 manifest 的 `unserved_app_keys`，不產出替代文案或薄頁。

## 產出與隱私

- `/{locale}/tools/purchase-worktime-sheet.html`：官方 50 locale 的完整工具、
  預先算好的範例表格、逐步公式、範圍限制與選用 App。
- `/{locale}/tools/results/purchase-worktime-sheet.csv`：不含個資的公共範例。
- `/{locale}/tools/hero-tasks.feed.json`：50 份原生語系 JSON Feed，含可下載範例、
  穩定 item ID、語意更新日期及完整 App Store 歸因連結。
- `data/hero-tasks/manifest.json`、schema、`sitemap_hero_tasks.xml`：
  真實支援範圍、來源 digest、成果 SHA-256 與 canonical 清單。
- 每語工具索引及既有第一順位答案接到免費成果。
  沒有該語答案的場合，沿用經驗證的本語 App guide 作導航，
  **不為補數量生成答案頁**。

生成器完全不連網。`hero-task-core.js` 同時供 Node 建置和瀏覽器運算，
避免靜態範例與互動結果各自實作。金額先轉整數最小單位；合計不累加已四捨五入的時間。
數量限制 1–999，每份最多 30 筆；價格、收入支援最多兩位小數；
單價與每小時收入各至多 100,000,000，以涵蓋 VND 等幣別的日常大額價格；
收入及每日工時須大於零，每日工時至多 24。限制同時公開於每語工具頁。
所有金額必須同幣別且含稅，不提供換匯、薪資、儲蓄預測或購買建議。

使用者輸入只在分頁記憶體內；下載是本機 Blob，不會變成公開成果、
URL 參數、feed 或資料集。離開頁面會清除編輯。CSP 禁止連線，
不使用帳號、Web Storage、IndexedDB、分析碼或第三方腳本。
CSV 使用 UTF-8 BOM、RFC 4180 引號、固定小數點，並阻止試算表公式注入。
網站的 `.gitattributes` 保留 CSV 的 CRLF 原始位元組，避免跨平台 checkout 破壞公布的 SHA-256。
表單必須等本機 JS 成功初始化才啟用；無 JS 時公共範例仍可直接下載。

## 本機生成與驗證

在 GrowthEngine 根目錄執行；不會 commit、push、部署、更新 live cache 或發送 IndexNow：

```sh
APP_STORE_PROVIDER_TOKEN=118326163 python3 -B geo/hero_tasks.py
APP_STORE_PROVIDER_TOKEN=118326163 python3 -B geo/hero_tasks.py --check
```

`GEO_PAGES` 或 `--pages-dir` 可指定隔離網站，`GEO_SITE` 決定公開 canonical host。
缺 provider token、native copy、已驗證 App ID、來源頁或 adapter 時，
必須在寫入任何成果前失敗。`--check` 不修復、不寫檔。
再次生成不改動相同 bytes／mtime／dateModified；只清理前次 manifest 擁有且未被修改的舊成果。

```sh
mkdir -p geo/.hero-validation
TMPDIR="$PWD/geo/.hero-validation" \
CHROME_BINARY="/path/to/an/isolated/Chromium/executable" \
PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest geo.tests.test_hero_tasks
```

測試用 unittest 與 Node 22+ 內建功能，沒有額外測試框架。
瀏覽器測試使用獨立 profile、loopback HTTP、CDP、真實 CSV 下載，
並拒絕頁面對外請求；50 locale 均驗最小與最大 viewport。
沒有 Chromium 不可跳過或宣稱通過。僅在缺少時，可把
`@puppeteer/browsers` 與 `chrome-headless-shell` 安裝到
`geo/.hero-validation/`；本次驗證使用 `152.0.7977.82`。
該目錄不進版控或網站。

## 擴充契約

1. 先查證下一款 App 的主承諾及真實可下載任務，不能從行銷標籤猜能力。
2. 為新 adapter 增加純 JS 核心、對應 Python renderer、完整 50 語文案及 golden cases。
   目前 renderer 僅接受 `purchase-worktime-v1` 的資料契約。
3. 在 `hero_tasks.json` 明確綁定 App key、App Store ID、來源 query 與公共範例。
   等價任務合併至既有 canonical；不接受同 adapter 複製多個 slug。
4. 通過錯誤／邊界／下載／注入防護／50 語／無 JS／冪等／pipeline 順序測試。
5. 把來源、JS/CSS、文案及測試同步到 `pages/_engine/geo/`。

`publish.py` 與 `geo-daily.yml` 會在跨頁處理後重建成果，再執行 Gate。
根層 feed 保留英文工具入口，專用 feed 負責完整 50 語覆蓋。
所有選用 App 的操作連結是 `pt + ct=geo_learn + mt=8`；
不以 App、語系或每份使用者成果再切碎 campaign。

## 發布與 readback

本機生成不等於部署，也不等於收錄。Pages upload 前會執行 `--check`；
部署後，獨立的 `hero_tasks_readback.py` 僅以 GET 比對 manifest 與每份公開
HTML、CSV、feed、JS/CSS 的 SHA-256。可用 Pages origin 做部署 readback，
但公開 canonical、feed 和 sitemap 一律使用 `site_config.PUBLIC_SITE`。
所有 readback 通過後，既有 IndexNow workflow 才能通知變更 URL。
IndexNow 的 200／202 只代表受理，不代表搜尋收錄。
