# 英雄任務成果工具

第一波是 **多筆購物價格 → 工作時間比較表 → CSV**，不是工時打卡或薪資工具。
HoursTag 與 HoursTag Lite 共用同一任務 canonical。依據是既有產品契約、
`hourstag_work_hours_tool.py` 及 publisher intent catalog；**不是已測得的搜尋量**。

第二波是 **多項保養「上次完成日＋間隔」→ 下次到期／剩餘天數／逾期 排程表 → CSV**
（`maintenance-next-due`，Mochi DoneStamp 6790800323），不是提醒、推播、行事曆同步或每日待辦。
月單位保留同一日、該月沒有則取月底（含閏年），與 App 契約一致；狀態為 overdue／due_soon（≤7 天）／ok，
表格依剩餘天數排序。任務層文案放在 `hero_tasks_i18n.json` 的 `tasks.maintenance-next-due`，
只覆蓋任務自己的 key，共用 key（remove／download／privacy…）沿用第一波，第一波輸出 bytes 不變。
每個 adapter 有自己的純 JS 核心與瀏覽器 UI（`hero-task-maintenance-core.js`／`-ui.js`），
共用 `hero-task.css` 並可加一份專屬樣式；資產以內容 digest 命名，第一波資產路徑不受第二波影響。
未配置 adapter 的 App 留在 manifest 的 `unserved_app_keys`，不產出替代文案或薄頁。

第二波另有兩個任務，同樣各自帶 core／UI 資產與 `tasks.<id>` 任務層文案，前兩個任務的輸出 bytes 不變：

- **專案收支損益表**（`project-profit`，MoneyTag 6801956402）：多筆收入／支出 → 收入合計、支出合計、
  利潤、毛利率、每小時淨收入 → CSV。金額轉整數最小單位相加；沒有收入時毛利率、沒有工時時每小時淨收入
  一律為空而不是 0；工時只接受 0.25–2000 的四分之一小時步進。同幣別、不換匯、不做稅務或會計建議，
  不綁 G+Money，也不是發票、薪資或記帳工具。
- **電池容量／循環磨耗區間表**（`battery-wear`，BattAI 6802423998）：使用者自己輸入的最大容量、
  選填循環次數與購入月份 → 每月磨耗 %、距 80% 月數、每月循環數 → CSV。依 BattAI 契約，
  每個數值都標「你提供／推估」，推估值只以觀測平均 ±25% 的區間呈現（低界取高磨耗率、高界取低磨耗率），
  永不輸出單一預測數字或健康分數；工具不量測、不讀取任何手機資料，也不給診斷或更換建議。

## 產出與隱私

- `/{locale}/tools/purchase-worktime-sheet.html`：官方 50 locale 的完整工具、
  預先算好的範例表格、逐步公式、範圍限制與選用 App。
- `/{locale}/tools/maintenance-next-due-sheet.html` 與 `/{locale}/tools/results/maintenance-next-due-sheet.csv`：
  第二波保養到期排程表；日期一律 ISO `YYYY-MM-DD`，間隔 1–3650（日／週／月），最多 30 項。
- `/{locale}/tools/results/purchase-worktime-sheet.csv`：不含個資的公共範例。
- `/{locale}/tools/project-profit-sheet.html` 與 `/{locale}/tools/results/project-profit-sheet.csv`：
  專案損益表；金額 0–100,000,000、至多兩位小數，收入與支出各至多 20 列。
- `/{locale}/tools/battery-wear-range-sheet.html` 與 `/{locale}/tools/results/battery-wear-range-sheet.csv`：
  電池磨耗區間表；容量 60–100 整數 %、循環 0–3000、購入月份 `YYYY-MM`（2007–2099、機齡 1–240 個月），至多 10 台，
  CSV 每列附「你提供／推估」來源欄。
- `/{locale}/tools/hero-tasks.feed.json`：50 份原生語系 JSON Feed，含可下載範例、
  穩定 item ID、語意更新日期及完整 App Store 歸因連結。
- `data/hero-tasks/manifest.json`、schema、`sitemap_hero_tasks.xml`：
  真實支援範圍、來源 digest、成果 SHA-256 與 canonical 清單。
- 只向既有、具完整 metadata／hreflang 與多項工具的索引插卡，不建立新的索引薄頁。
  缺少合格索引時，導覽及 feed 改指該語既有完整首頁／hub；都不存在時不輸出導覽，
  feed 則直接指向完整工具頁。舊版自行產生、僅有標題與 hero 卡片的索引會安全清理，
  並以 `retired_indexes` 保持冪等；已有其他內容者不會被刪除。
- 既有第一順位答案及 App guide 的原始 h1、摘要和主要 CTA 都先於 hero 資源卡。
  插入點採真實 HTML 元素邊界，位於 CTA managed block 之外，
  不重寫原始內容、microformats、metadata 或 hreflang。
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

## 第二層到達路徑與 AI 引用

- **第二層插卡（零新 URL）**：除第一順位答案／App guide 外，同 App、同語、`answers/` 下已由
  `gen_app_decision_cards` 放入該 App 決策卡（`<!-- app-decision-card:start/end -->` 內含該 App Store ID）的
  其他答案頁，每 App 每語最多 3 頁（路徑排序取前三），插同一張 `hero-task-resources-v1` 卡，仍遵守
  h1→原 CTA→hero block→h2 與真實元素邊界；沒有合格邊界的頁面直接略過，不改寫。
  manifest 的 `secondary_integrations` 逐 `{locale}/{app}` 列出，`integrations` 一併包含。
- **HowTo + Dataset JSON-LD**：每份工具頁在 `WebApplication` 之後另有一段 JSON-LD：`HowTo`（步驟＝該語
  formula／limits 文案、`isAccessibleForFree`）與 `Dataset`（公共範例 CSV 的 `distribution`、CC BY 4.0、
  `includedInDataCatalog` 指向 `/data/`）。**永遠不得輸出 `aggregateRating`／`review`**。
- **分發線**：`gen_llms.py` 的 llms.txt／llms-full.txt 與 `gen_data_hub.py` 的 `/data/` 索引只列 en-US 完整工具頁
  （不列 CSV）；`social/gen_standard_site.py` 把 en-US 工具頁當作額外 Standard.site 文件（`editorial_kind: tool`，
  不佔每 App 的 deep 文件名額）；IndexNow 由 `pages.yml` 成功（含 `verify_hero`）後的 `indexnow-daily`
  透過 `sitemap_index.xml` 中的 `sitemap_hero_tasks.xml` 提交。

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
重繪完整工具頁前會用 `sync_standard_site.preserve_managed_links` 保留已驗證的
publication／document links，再計算最終成果 SHA-256；反覆 `sync → hero` 不得漂移。

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
   目前 renderer 接受 `purchase-worktime-v1`、`maintenance-next-due-v1`、`project-profit-v1`
   與 `battery-wear-range-v1` 四種資料契約；
   新 adapter 在 `ADAPTER_ASSETS` 登錄自己的 core／ui（可選 extra_css），任務層 key 登錄於 `TASK_KEYS`。
3. 在 `hero_tasks.json` 明確綁定 App key、App Store ID、來源 query 與公共範例。
   等價任務合併至既有 canonical；不接受同 adapter 複製多個 slug。
4. 通過錯誤／邊界／下載／注入防護／50 語／無 JS／冪等／pipeline 順序測試。
   另有 50 頁 managed links、40 舊薄頁／10 完整索引，以及 100 頁原始
   h1／summary／CTA 優先與 microformats 保留矩陣。
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
